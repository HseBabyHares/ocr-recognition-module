"""Recovery dispatcher for process result and dead-letter outbox rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sird_workflow._process_outbox_mixins import (
    _ProcessOutboxPersistenceMixin,
    _ProcessOutboxPublicationMixin,
)
from sird_workflow.db import session_factory

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session, sessionmaker

    from sird_workflow.dead_letter import DeadLetterPublisher
    from sird_workflow.producer import TaskProducer


@dataclass(frozen=True, slots=True)
class ProcessOutboxDispatchReport:
    """Counts from one bounded process-outbox dispatch pass."""

    result_attempted: int
    result_published: int
    result_failed: int
    dead_letter_attempted: int
    dead_letter_acknowledged: int
    dead_letter_failed: int


# A descriptive alias for callers that use the shorter report name.
ProcessDispatchReport = ProcessOutboxDispatchReport


class ProcessOutboxDispatcher(
    _ProcessOutboxPersistenceMixin, _ProcessOutboxPublicationMixin
):
    """Publish durable process results and dead letters after commit.

    Pending rows are loaded in short read transactions. The broker calls happen
    after those transactions close. A row is marked only after its publication
    succeeds, and a dead-letter row is marked only after an explicit positive
    broker acknowledgement.
    """

    def __init__(
        self,
        engine: Engine,
        result_producer: TaskProducer,
        dead_letter_publisher: DeadLetterPublisher,
    ) -> None:
        self._session_factory: sessionmaker[Session] = session_factory(engine)
        self._result_producer = result_producer
        self._dead_letter_publisher = dead_letter_publisher

    def dispatch_pending(
        self, limit: int = 100
    ) -> ProcessOutboxDispatchReport:
        """Publish up to ``limit`` pending rows from each process outbox."""
        if limit <= 0:
            raise ValueError("limit must be positive")
        result_rows = self._pending_result_rows(limit)
        result_counts = self._dispatch_results(result_rows)
        dead_letter_rows = self._pending_dead_letter_rows(limit)
        dead_letter_counts = self._dispatch_dead_letters(dead_letter_rows)
        return ProcessOutboxDispatchReport(
            result_attempted=len(result_rows),
            result_published=result_counts[0],
            result_failed=result_counts[1],
            dead_letter_attempted=len(dead_letter_rows),
            dead_letter_acknowledged=dead_letter_counts[0],
            dead_letter_failed=dead_letter_counts[1],
        )
