"""Delivery handling and terminal acknowledgement ordering."""

from __future__ import annotations

from typing import Any

from sird_workflow._consumer_decoder import _DecodedMessage
from sird_workflow._consumer_models import TaskConsumerDecision
from sird_workflow._consumer_state import _ConsumerState
from sird_workflow._consumer_tools import _ConsumerTools
from sird_workflow.cancellation import CancellationToken
from sird_workflow.invalid_task_event_error import InvalidTaskEventError
from sird_workflow.process_outcome import ProcessOutcome
from sird_workflow.task_event import TaskEvent

RETRY_DECISION = "RETRY_WITHOUT_ACK"
INVALID_DECISION = "INVALID_EVENT"
TERMINAL_DECISION = "TERMINAL_ACK_READY"


class _ConsumerDelivery(_ConsumerState):
    """Decode and process one task delivery."""

    async def handle_delivery(
        self, message: Any, cancellation: CancellationToken | None = None
    ) -> TaskConsumerDecision:
        decision = self.handle_message(
            message, cancellation=cancellation, acknowledge=False
        )
        actions = {
            "terminal_ack_ready": "ack",
            "invalid_event": "reject",
        }
        action = actions.get(decision.value)
        if action is not None:
            kwargs = {"requeue": False} if action == "reject" else {}
            await _ConsumerTools.await_message_action(
                message, action, **kwargs
            )
        elif decision.value == "retry_without_ack":
            await self._retry_or_reject(message)
        return decision

    def handle_message(
        self,
        message: Any,
        cancellation: CancellationToken | None = None,
        *,
        acknowledge: bool = True,
    ) -> TaskConsumerDecision:
        position = _ConsumerTools.message_position(message)
        if self._blocked(position):
            return self._decision(RETRY_DECISION)
        decoded = self._decode_message(message)
        if decoded is None:
            self._block(position)
            return self._decision(INVALID_DECISION)
        return self._handle_decoded(
            decoded, position, cancellation, acknowledge
        )

    async def _retry_or_reject(self, message: Any) -> None:
        decoded = self._decode_message(message)
        if decoded is not None and self._retry_producer is not None:
            await self._retry_producer.publish_async(
                topic=self._config.retry_route,
                key=decoded.event.task_id,
                payload=_ConsumerTools.event_payload(decoded.event),
            )
            await _ConsumerTools.await_message_action(message, "ack")
            return
        await _ConsumerTools.await_message_action(
            message, "reject", requeue=True
        )

    def _handle_decoded(
        self,
        decoded: _DecodedMessage,
        position: str | None,
        cancellation: CancellationToken | None,
        acknowledge: bool,
    ) -> TaskConsumerDecision:
        outcome = self._execute_event(
            decoded.event, decoded.delivery_id, position, cancellation
        )
        if not isinstance(outcome, ProcessOutcome):
            return outcome
        if not outcome.terminal:
            self._block(position, delay_seconds=outcome.retry_after_seconds)
            return self._decision(RETRY_DECISION)
        return self._finish_terminal(
            decoded.transport,
            decoded.event,
            outcome,
            position,
            acknowledge,
        )

    def _execute_event(
        self,
        event: TaskEvent,
        delivery_id: str,
        position: str | None,
        cancellation: CancellationToken | None,
    ) -> ProcessOutcome | TaskConsumerDecision:
        try:
            reconciled = self._reconcile(event)
        except InvalidTaskEventError:
            self._block(position)
            return self._decision(INVALID_DECISION)
        except Exception:
            self._block(position)
            return self._decision(RETRY_DECISION)
        active_cancellation = cancellation or CancellationToken()
        if position is not None:
            self._active_cancellations[position] = active_cancellation
        try:
            return reconciled or self._process_service.process_event(
                event,
                self._worker_id,
                delivery_id,
                cancellation=active_cancellation,
            )
        except InvalidTaskEventError:
            self._block(position)
            return self._decision(INVALID_DECISION)
        except Exception:
            self._block(position)
            return self._decision(RETRY_DECISION)
        finally:
            if position is not None:
                self._active_cancellations.pop(position, None)

    def _dispatch_and_check(
        self, event: TaskEvent, outcome: ProcessOutcome
    ) -> bool:
        self._outbox_dispatcher.dispatch_pending()
        return self._terminal_outboxes_ready(event, outcome)

    def _finish_terminal(
        self,
        transport: Any,
        event: TaskEvent,
        outcome: ProcessOutcome,
        position: str | None,
        acknowledge: bool,
    ) -> TaskConsumerDecision:
        try:
            outboxes_ready = self._dispatch_and_check(event, outcome)
        except Exception:
            self._block(position)
            return self._decision(RETRY_DECISION)
        if not outboxes_ready:
            self._block(position)
            return self._decision(RETRY_DECISION)
        if acknowledge:
            try:
                self._acknowledger(transport)
            except Exception:
                self._block(position)
                return self._decision(RETRY_DECISION)
        self._clear_position(position)
        return self._decision(TERMINAL_DECISION)
