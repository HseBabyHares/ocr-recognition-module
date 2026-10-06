"""Shared typed state contract for composed RabbitMQ consumer mixins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from sird_workflow._consumer_models import (
    MessageAcknowledger,
    RabbitMQConsumerConfig,
    TaskConsumerDecision,
)
from sird_workflow.cancellation import CancellationToken
from sird_workflow.process import ProcessService
from sird_workflow.process_outbox import ProcessOutboxDispatcher
from sird_workflow.process_outcome import ProcessOutcome
from sird_workflow.producer import RabbitMQTaskProducer
from sird_workflow.task_event import TaskEvent

if TYPE_CHECKING:
    from sird_workflow._consumer_decoder import _DecodedMessage


class _ConsumerStateAttributes(Protocol):
    """Attributes shared by composed RabbitMQ consumer mixins."""

    _config: RabbitMQConsumerConfig
    _process_service: ProcessService
    _outbox_dispatcher: ProcessOutboxDispatcher
    _worker_id: str
    _consumer: Any | None
    _connection: Any | None
    _channel: Any | None
    _queue: Any | None
    _retry_producer: RabbitMQTaskProducer | None
    _acknowledger: MessageAcknowledger
    _blocked_ids: dict[str, float]
    _active_cancellations: dict[object, CancellationToken]
    _decision_type: type[TaskConsumerDecision]
    _session_factory: sessionmaker[Session] | None


class _ConsumerConnectionMethods(Protocol):
    """Connection and delivery lifecycle methods."""

    async def handle_delivery(self, message, cancellation=None) -> Any: ...

    async def _connect(self) -> None: ...

    async def _consume_delivery(self, message: Any) -> None: ...

    def _create_retry_producer(self) -> RabbitMQTaskProducer: ...

    async def _declare_queue(self) -> None: ...

    async def _start_consuming(self) -> None: ...


class _ConsumerMessageMethods(Protocol):
    """Message handling and position methods."""

    def handle_message(
        self,
        message: Any,
        cancellation: CancellationToken | None = None,
        *,
        acknowledge: bool = True,
    ) -> TaskConsumerDecision: ...

    @classmethod
    def _delivery_route(cls, delivery: Any) -> Any: ...

    def _blocked(self, position: str | None) -> bool: ...

    def _block(
        self, position: str | None, *, delay_seconds: float = 0
    ) -> None: ...

    def _clear_position(self, position: str | None) -> None: ...

    def _decode_message(self, message: Any) -> _DecodedMessage | None: ...


class _ConsumerPersistenceMethods(Protocol):
    """Decision and persistence methods."""

    def _decision(self, name: str) -> TaskConsumerDecision: ...

    def _reconcile(self, event: TaskEvent) -> ProcessOutcome | None: ...

    def _terminal_outboxes_ready(
        self, event: TaskEvent, outcome: ProcessOutcome
    ) -> bool: ...

    def _resolve_session_factory(
        self,
        *,
        engine: Engine | None,
        session_factory: sessionmaker[Session] | None,
    ) -> sessionmaker[Session] | None: ...

    def _ack_with_message(self, message: Any) -> None: ...


class _ConsumerProcessingMethods(
    _ConsumerMessageMethods,
    _ConsumerPersistenceMethods,
    Protocol,
):
    """Message processing and persistence methods."""


class _ConsumerMethods(
    _ConsumerConnectionMethods,
    _ConsumerProcessingMethods,
    Protocol,
):
    """Complete consumer operation methods."""


class _ConsumerState(
    _ConsumerStateAttributes,
    _ConsumerMethods,
    Protocol,
):
    """Attributes and cross-mixin methods of ``RabbitMQTaskConsumer``."""
