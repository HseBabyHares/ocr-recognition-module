"""Durable task processing and consumer operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from sird_workflow import (
    event_record_validation,
    ocr_executor,
    task_claim,
    task_completion,
    task_reconciliation,
    task_terminal_writer,
)
from sird_workflow.cancellation import CancellationToken
from sird_workflow.db import session_factory as make_session_factory
from sird_workflow.process_outcome import ProcessOutcome
from sird_workflow.task_event import TaskEvent

if TYPE_CHECKING:
    from sird_workflow.ocr_client import OcrClient


class ProcessService:
    """Coordinate claim, OCR execution, completion, and reconciliation."""

    def __init__(
        self,
        engine: Engine,
        ocr_client: OcrClient,
        *,
        result_topic: str = "sird.result.v1",
        dead_letter_topic: str = "sird.task.terminal.v1",
    ) -> None:
        self._session_factory: sessionmaker[Session] = make_session_factory(
            engine
        )
        terminal_writer = task_terminal_writer.TaskTerminalWriter(
            result_topic, dead_letter_topic
        )
        reconciliation = task_reconciliation.TaskReconciliation()
        self._claim = task_claim.TaskClaim(
            self._session_factory, terminal_writer, reconciliation
        )
        self._completion = task_completion.TaskCompletion(
            self._session_factory, terminal_writer
        )
        self._reconciliation = reconciliation
        self._ocr_executor = ocr_executor.OcrExecutor(ocr_client)

    def process_event(
        self,
        event: TaskEvent,
        worker_id: str,
        delivery_id: str,
        cancellation: CancellationToken | None = None,
    ) -> ProcessOutcome:
        """Process one delivery using PostgreSQL row locks for fencing."""

        if not isinstance(event, TaskEvent):
            raise TypeError("process_event expects a decoded TaskEvent")
        event_record_validation.require_text(worker_id, "worker_id")
        event_record_validation.require_text(delivery_id, "delivery_id")
        lease, duplicate = self._claim.claim(event, worker_id, delivery_id)
        if duplicate is not None:
            return duplicate
        ocr_result = self._ocr_executor.execute(event, cancellation)
        return self._completion.complete(event, delivery_id, lease, ocr_result)

    def reconcile_event(self, event: TaskEvent) -> ProcessOutcome | None:
        """Return a terminal result before another attempt starts."""
        if not isinstance(event, TaskEvent):
            raise TypeError("reconcile_event expects a decoded TaskEvent")
        with self._session_factory() as session:
            return self._reconciliation.reconcile(session, event)
