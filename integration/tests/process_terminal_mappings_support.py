from __future__ import annotations

import datetime as dt
from typing import Any

import sqlalchemy as sa
from process_terminal_mappings_setup import service
from sird_workflow import db as workflow_db
from sird_workflow.ocr_call_result import OcrCallResult
from sird_workflow.ocr_outcome import OcrOutcome
from sird_workflow.task_event import TaskEvent
from sqlalchemy.engine import Engine


class MappingConfig:
    retention_seconds = 3600
    ocr_deadline_seconds = 35.0
    worker_id = "worker-mapping"
    delivery_id = "delivery-mapping"


def event(*, max_attempts: int = 2) -> TaskEvent:
    now = dt.datetime.now(dt.UTC)
    return TaskEvent(
        event_id="submitted-mapping",
        task_id="task-mapping",
        request_id="request-mapping",
        artifact_ref="artifact-synthetic",
        policy={},
        retention_seconds=MappingConfig.retention_seconds,
        max_attempts=max_attempts,
        submitted_at=now,
        retention_expires_at=now + dt.timedelta(hours=1),
    )


class FixedOcr:
    def __init__(
        self, outcome: OcrOutcome, *, error: str | None = None
    ) -> None:
        self.outcome = outcome
        self.error = error
        self.calls = 0

    def recognize(
        self, event: TaskEvent, *, deadline_seconds: float
    ) -> OcrCallResult:
        assert deadline_seconds == MappingConfig.ocr_deadline_seconds
        self.calls += 1
        return OcrCallResult(
            self.outcome, {"synthetic": self.outcome.value}, self.error
        )


class MappingAssertions:
    def terminal_response(
        self,
        first: Any,
        duplicate: Any,
        outcome: OcrOutcome,
        status: str,
        ocr: FixedOcr,
    ) -> None:
        assert (
            first.status,
            first.outcome,
            first.attempt_number,
            first.result_event_id,
            first.dead_letter_event_id,
            duplicate,
            ocr.calls,
        ) == (
            status,
            outcome.value,
            1,
            "submitted-mapping:result",
            None,
            first,
            1,
        )

    def terminal_task(
        self, task: Any, status: str, outcome: OcrOutcome
    ) -> None:
        assert (
            task is not None
            and task.status == status
            and task.result == {"synthetic": outcome.value}
        )

    def terminal_outbox(
        self, result_row: Any, dead_letter_count: Any, outcome: OcrOutcome
    ) -> None:
        assert result_row is not None
        assert (
            result_row.payload["event_type"],
            result_row.payload["outcome"],
            result_row.payload["result"],
            dead_letter_count,
        ) == (
            "sird.task.result.v1",
            outcome.value,
            {"synthetic": outcome.value},
            0,
        )

    def retry(
        self, retry: Any, result_count: Any, dead_letter_count: Any
    ) -> None:
        assert (
            retry.status,
            retry.outcome,
            retry.attempt_number,
            retry.retry_after_seconds,
            retry.result_event_id,
            retry.dead_letter_event_id,
            result_count,
            dead_letter_count,
        ) == ("retrying", OcrOutcome.TRANSIENT.value, 1, 1.0, None, None, 0, 0)

    def terminal_retry(
        self, terminal: Any, duplicate: Any, ocr: FixedOcr
    ) -> None:
        assert (
            terminal.status,
            terminal.outcome,
            terminal.attempt_number,
            terminal.result_event_id,
            terminal.dead_letter_event_id,
            duplicate.status,
            duplicate.outcome,
            duplicate.result_event_id,
            duplicate.attempt_number,
            ocr.calls,
        ) == (
            "failed",
            OcrOutcome.PERMANENT.value,
            2,
            "submitted-mapping:result",
            "submitted-mapping:dead-letter",
            terminal.status,
            terminal.outcome,
            terminal.result_event_id,
            terminal.attempt_number,
            2,
        )

    def retry_outbox(self, engine: Engine) -> None:
        with workflow_db.session_factory(engine)() as session:
            result_row = session.scalar(
                sa.select(workflow_db.TaskResultOutbox)
            )
            dead_letter = session.scalar(
                sa.select(workflow_db.TaskDeadLetterOutbox)
            )
        assert result_row is not None and dead_letter is not None
        assert (
            result_row.payload["outcome"],
            result_row.payload["error"],
            dead_letter.payload["event_type"],
            dead_letter.payload["reason"],
        ) == (
            OcrOutcome.PERMANENT.value,
            "temporary synthetic failure",
            "sird.task.dead-letter.v1",
            "temporary synthetic failure",
        )

    def terminal_rows(self, engine: Engine) -> tuple[Any, Any, Any]:
        with workflow_db.session_factory(engine)() as session:
            task = session.get(workflow_db.TaskRecord, "task-mapping")
            result_row = session.scalar(
                sa.select(workflow_db.TaskResultOutbox)
            )
            count = session.scalar(
                sa.select(sa.func.count()).select_from(
                    workflow_db.TaskDeadLetterOutbox
                )
            )
        return task, result_row, count


class TerminalScenario:
    def __init__(
        self,
        outcome: OcrOutcome,
        status: str,
        *,
        error: str = "synthetic terminal detail",
    ) -> None:
        self.event_value = event()
        self.ocr = FixedOcr(outcome, error=error)
        self.status = status
        self.outcome = outcome
        process_service, engine = service(self.event_value, self.ocr)
        self.process_service = process_service
        self.engine = engine

    def run(self) -> None:
        first = self.process_service.process_event(
            self.event_value,
            MappingConfig.worker_id,
            MappingConfig.delivery_id,
        )
        duplicate = self.process_service.process_event(
            self.event_value,
            MappingConfig.worker_id,
            MappingConfig.delivery_id,
        )
        MappingAssertions().terminal_response(
            first, duplicate, self.outcome, self.status, self.ocr
        )
        rows = MappingAssertions().terminal_rows(self.engine)
        MappingAssertions().terminal_task(rows[0], self.status, self.outcome)
        MappingAssertions().terminal_outbox(rows[1], rows[2], self.outcome)

    def run_retry(self) -> None:
        retry = self.process_service.process_event(
            self.event_value,
            MappingConfig.worker_id,
            MappingConfig.delivery_id,
        )
        result_count, dead_letter_count = self._retry_outbox_counts()
        self._expire_attempt()
        self.ocr.error = "temporary synthetic failure"
        terminal = self.process_service.process_event(
            self.event_value,
            MappingConfig.worker_id,
            MappingConfig.delivery_id,
        )
        duplicate = self.process_service.process_event(
            self.event_value,
            MappingConfig.worker_id,
            MappingConfig.delivery_id,
        )
        MappingAssertions().retry(retry, result_count, dead_letter_count)
        MappingAssertions().terminal_retry(terminal, duplicate, self.ocr)
        MappingAssertions().retry_outbox(self.engine)

    def _expire_attempt(self) -> None:
        with (
            workflow_db.session_factory(self.engine)() as session,
            session.begin(),
        ):
            attempt = session.get(
                workflow_db.TaskAttemptRecord, self.event_value.task_id
            )
            assert attempt is not None
            attempt.next_attempt_at = dt.datetime.now(dt.UTC) - dt.timedelta(
                seconds=1
            )

    def _retry_outbox_counts(self) -> tuple[int, int]:
        with workflow_db.session_factory(self.engine)() as session:
            return (
                session.query(workflow_db.TaskResultOutbox).count(),
                session.query(workflow_db.TaskDeadLetterOutbox).count(),
            )
