"""Recovery dispatcher for durable task outbox rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import and_, select, update
from sqlalchemy.engine import CursorResult, Engine
from sqlalchemy.orm import Session, sessionmaker

from sird_workflow.db import TaskOutbox, session_factory
from sird_workflow.producer import TaskProducer


@dataclass(frozen=True, slots=True)
class DispatchReport:
    """Counts from one bounded pending-outbox dispatch pass."""

    attempted: int
    published: int
    failed: int

    @property
    def selected(self) -> int:
        """Return the number of rows selected for publication."""

        return self.attempted


# Descriptive alias for callers that prefer the outbox-specific name.
OutboxDispatchReport = DispatchReport


class TaskOutboxDispatcher:
    """Publish pending task events without invoking OCR or creating events."""

    def __init__(self, engine: Engine, producer: TaskProducer) -> None:
        self._session_factory: sessionmaker[Session] = session_factory(engine)
        self._producer = producer

    def dispatch_pending(self, limit: int = 100) -> DispatchReport:
        """Publish up to ``limit`` pending rows and mark acknowledged rows.

        Pending rows are read in a short transaction. Publication happens after
        that transaction closes. A producer failure leaves its row pending and
        does not stop other selected rows from being attempted.
        """

        if limit <= 0:
            raise ValueError("limit must be positive")

        rows = self._pending_rows(limit)
        published = 0
        failed = 0
        for row in rows:
            try:
                self._producer.publish(
                    topic=row.topic,
                    key=row.task_id,
                    payload=row.payload,
                )
            except Exception:
                failed += 1
                continue
            if self._mark_published(row.event_id):
                published += 1

        return DispatchReport(
            attempted=len(rows),
            published=published,
            failed=failed,
        )

    def _pending_rows(self, limit: int) -> list[TaskOutbox]:
        with self._session_factory() as session, session.begin():
            return list(
                session.scalars(
                    select(TaskOutbox)
                    .where(TaskOutbox.published_at.is_(None))
                    .order_by(TaskOutbox.created_at, TaskOutbox.event_id)
                    .limit(limit)
                )
            )

    def _mark_published(self, event_id: str) -> bool:
        with self._session_factory() as session, session.begin():
            update_result = cast(
                CursorResult[Any],
                session.execute(
                    update(TaskOutbox)
                    .where(
                        and_(
                            TaskOutbox.event_id == event_id,
                            TaskOutbox.published_at.is_(None),
                        )
                    )
                    .values(published_at=datetime.now(UTC))
                ),
            )
            return update_result.rowcount == 1
