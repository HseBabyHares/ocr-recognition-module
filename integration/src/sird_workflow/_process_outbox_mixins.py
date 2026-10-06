"""Private persistence and publication operations for process outboxes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol, cast

from sqlalchemy import and_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, sessionmaker

from sird_workflow.db import (
    TaskDeadLetterOutbox,
    TaskRecord,
    TaskResultOutbox,
)
from sird_workflow.dead_letter import (
    BrokerAcknowledgement,
    DeadLetterEvent,
    DeadLetterOutbox,
    DeadLetterPublisher,
)
from sird_workflow.producer import TaskProducer


class _PersistenceHost(Protocol):
    _session_factory: sessionmaker[Session]


class _PublicationHost(_PersistenceHost, Protocol):
    _result_producer: TaskProducer
    _dead_letter_publisher: DeadLetterPublisher

    def _suppress_expired_result(self, event_id: str) -> bool: ...

    def _mark_result_published(self, event_id: str) -> bool: ...

    def _mark_dead_letter_acknowledged(
        self, event_id: str, acknowledged_at: datetime | None
    ) -> bool: ...
    def _publish_result(self, row: TaskResultOutbox) -> None: ...

    def _publish_dead_letter(
        self, row: TaskDeadLetterOutbox
    ) -> BrokerAcknowledgement: ...


class _ProcessOutboxPersistenceMixin:
    def _pending_result_rows(
        self: _PersistenceHost, limit: int
    ) -> list[TaskResultOutbox]:
        with self._session_factory() as session, session.begin():
            return list(
                session.scalars(
                    select(TaskResultOutbox)
                    .where(
                        TaskResultOutbox.published_at.is_(None),
                        TaskResultOutbox.suppressed_at.is_(None),
                    )
                    .order_by(
                        TaskResultOutbox.created_at,
                        TaskResultOutbox.event_id,
                    )
                    .limit(limit)
                )
            )

    def _pending_dead_letter_rows(
        self: _PersistenceHost, limit: int
    ) -> list[TaskDeadLetterOutbox]:
        with self._session_factory() as session, session.begin():
            return list(
                session.scalars(
                    select(TaskDeadLetterOutbox)
                    .where(TaskDeadLetterOutbox.acknowledged_at.is_(None))
                    .order_by(
                        TaskDeadLetterOutbox.created_at,
                        TaskDeadLetterOutbox.event_id,
                    )
                    .limit(limit)
                )
            )

    def _suppress_expired_result(
        self: _PersistenceHost, event_id: str
    ) -> bool:
        with self._session_factory() as session, session.begin():
            row = session.get(TaskResultOutbox, event_id, with_for_update=True)
            if (
                row is None
                or row.published_at is not None
                or row.suppressed_at is not None
            ):
                return False
            task = session.get(TaskRecord, row.task_id, with_for_update=True)
            if task is None or not _is_expired(task.retention_expires_at):
                return False
            row.suppressed_at = datetime.now(UTC)
            row.suppression_reason = "retention_expired"
            return True

    def _mark_result_published(self: _PersistenceHost, event_id: str) -> bool:
        with self._session_factory() as session, session.begin():
            update_result = cast(
                CursorResult[Any],
                session.execute(
                    update(TaskResultOutbox)
                    .where(
                        and_(
                            TaskResultOutbox.event_id == event_id,
                            TaskResultOutbox.published_at.is_(None),
                            TaskResultOutbox.suppressed_at.is_(None),
                        )
                    )
                    .values(published_at=datetime.now(UTC))
                ),
            )
            return update_result.rowcount == 1

    def _mark_dead_letter_acknowledged(
        self: _PersistenceHost,
        event_id: str,
        acknowledged_at: datetime | None,
    ) -> bool:
        with self._session_factory() as session, session.begin():
            update_result = cast(
                CursorResult[Any],
                session.execute(
                    update(TaskDeadLetterOutbox)
                    .where(
                        and_(
                            TaskDeadLetterOutbox.event_id == event_id,
                            TaskDeadLetterOutbox.acknowledged_at.is_(None),
                        )
                    )
                    .values(
                        acknowledged_at=acknowledged_at or datetime.now(UTC)
                    )
                ),
            )
            return update_result.rowcount == 1


class _ProcessOutboxPublicationMixin:
    def _dispatch_results(
        self: _PublicationHost, rows: list[TaskResultOutbox]
    ) -> tuple[int, int]:
        published = 0
        failed = 0
        for row in rows:
            if self._suppress_expired_result(row.event_id):
                continue
            try:
                self._publish_result(row)
            except Exception:
                failed += 1
                continue
            if self._mark_result_published(row.event_id):
                published += 1
        return published, failed

    def _dispatch_dead_letters(
        self: _PublicationHost, rows: list[TaskDeadLetterOutbox]
    ) -> tuple[int, int]:
        acknowledged = 0
        failed = 0
        for row in rows:
            try:
                ack = self._publish_dead_letter(row)
            except Exception:
                failed += 1
                continue
            if self._mark_dead_letter_acknowledged(
                row.event_id, ack.acknowledged_at
            ):
                acknowledged += 1
        return acknowledged, failed

    def _publish_result(self: _PublicationHost, row: TaskResultOutbox) -> None:
        self._result_producer.publish(
            topic=row.topic,
            key=row.task_id,
            payload=row.payload,
        )

    def _publish_dead_letter(
        self: _PublicationHost, row: TaskDeadLetterOutbox
    ) -> BrokerAcknowledgement:
        event = DeadLetterEvent(
            event_id=row.event_id,
            task_id=row.task_id,
            topic=row.topic,
            payload=row.payload,
            created_at=row.created_at,
        )
        acknowledgement = self._dead_letter_publisher.publish(event)
        _require_acknowledgement(event, acknowledgement)
        return acknowledgement


def _is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= datetime.now(UTC)


def _require_acknowledgement(
    event: DeadLetterEvent, acknowledgement: BrokerAcknowledgement
) -> None:
    """Validate the publisher result before changing durable state."""
    DeadLetterOutbox(event=event).record_acknowledgement(acknowledgement)
    if not acknowledgement.acknowledged:
        raise ValueError("dead-letter publication was not acknowledged")
