"""Durable outbox checks and acknowledgement operations."""

from __future__ import annotations

import inspect
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from sird_workflow._consumer_state import _ConsumerState
from sird_workflow.db import TaskDeadLetterOutbox, TaskResultOutbox
from sird_workflow.db import session_factory as make_session_factory
from sird_workflow.process_outcome import ProcessOutcome
from sird_workflow.task_event import TaskEvent


class _ConsumerPersistence(_ConsumerState):
    """Durable outbox and acknowledgement operations."""

    def _terminal_outboxes_ready(
        self, event: TaskEvent, outcome: ProcessOutcome
    ) -> bool:
        if self._session_factory is None or outcome.result_event_id is None:
            return False
        with self._session_factory() as session:
            result_outbox = session.scalar(
                select(TaskResultOutbox).where(
                    and_(
                        TaskResultOutbox.task_id == event.task_id,
                        TaskResultOutbox.event_id == outcome.result_event_id,
                    )
                )
            )
            if result_outbox is None or (
                result_outbox.published_at is None
                and result_outbox.suppressed_at is None
            ):
                return False
            dead_letters = list(
                session.scalars(
                    select(TaskDeadLetterOutbox).where(
                        and_(
                            TaskDeadLetterOutbox.task_id == event.task_id,
                            TaskDeadLetterOutbox.source_event_id
                            == event.event_id,
                        )
                    )
                )
            )
            has_dead_letter = outcome.dead_letter_event_id is None or any(
                row.event_id == outcome.dead_letter_event_id
                for row in dead_letters
            )
            return has_dead_letter and all(
                row.acknowledged_at is not None for row in dead_letters
            )

    def _ack_with_message(self, message: Any) -> None:
        ack = getattr(message, "ack", None)
        if not callable(ack):
            raise TypeError("RabbitMQ delivery does not expose manual ack")
        ack_result = ack()
        if inspect.isawaitable(ack_result):
            raise RuntimeError(
                "use handle_delivery for asynchronous acknowledgements"
            )

    def _resolve_session_factory(
        self,
        *,
        engine: Engine | None,
        session_factory: sessionmaker[Session] | None,
    ) -> sessionmaker[Session] | None:
        if session_factory is not None:
            return session_factory
        if engine is not None:
            return make_session_factory(engine)
        for source in (self._outbox_dispatcher, self._process_service):
            candidate = getattr(source, "_session_factory", None)
            if callable(candidate):
                return candidate
        return None

    def _reconcile(self, event: TaskEvent) -> ProcessOutcome | None:
        method = getattr(self._process_service, "reconcile_event", None)
        if callable(method):
            return method(event)
        return None
