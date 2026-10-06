"""Claim transaction for fenced task attempts."""

import datetime as datetime_module
from typing import Any

from sqlalchemy import select

from sird_workflow import (
    attempt_record,
    attempts,
    ocr_call_result,
    ocr_outcome,
    process_outcome,
    task_event,
)
from sird_workflow import (
    db as workflow_db,
)
from sird_workflow import (
    event_record_validation as event_validation,
)
from sird_workflow import (
    invalid_task_event_error as invalid_event,
)


class TaskClaim:
    """Own the transaction that locks and claims a task attempt."""

    def __init__(
        self,
        session_factory: Any,
        terminal_writer: Any,
        reconciliation: Any,
    ) -> None:
        self._session_factory = session_factory
        self._terminal_writer = terminal_writer
        self._reconciliation = reconciliation

    def claim(
        self,
        event: task_event.TaskEvent,
        worker_id: str,
        delivery_id: str,
    ) -> tuple[attempts.AttemptLease, process_outcome.ProcessOutcome | None]:
        with self._session_factory() as session, session.begin():
            task, attempt = self._locked_records(session, event)
            if attempt.terminal_outcome is not None:
                return self._reconcile_terminal(
                    session, task, attempt, event, worker_id
                )
            retry = self._scheduled_retry(task, attempt, event, worker_id)
            if retry is not None:
                return retry
            return self._claim_budget(
                session, task, attempt, event, (worker_id, delivery_id)
            )

    def _locked_records(
        self, session: Any, event: task_event.TaskEvent
    ) -> tuple[workflow_db.TaskRecord, workflow_db.TaskAttemptRecord]:
        task = session.scalar(
            select(workflow_db.TaskRecord)
            .where(workflow_db.TaskRecord.task_id == event.task_id)
            .with_for_update()
        )
        if task is None:
            raise invalid_event.InvalidTaskEventError(
                f"task {event.task_id!r} does not exist"
            )
        event_validation.validate_event_against_task(task, event)
        attempt = session.scalar(
            select(workflow_db.TaskAttemptRecord)
            .where(workflow_db.TaskAttemptRecord.task_id == event.task_id)
            .with_for_update()
        )
        if attempt is None:
            attempt = workflow_db.TaskAttemptRecord(
                task_id=event.task_id,
                max_attempts=event.max_attempts,
                updated_at=datetime_module.datetime.now(datetime_module.UTC),
            )
            session.add(attempt)
            session.flush()
        if attempt.max_attempts != event.max_attempts:
            raise invalid_event.InvalidTaskEventError(
                "task event attempt budget does not match durable state"
            )
        return task, attempt

    def _reconcile_terminal(
        self,
        session: Any,
        task: workflow_db.TaskRecord,
        attempt: workflow_db.TaskAttemptRecord,
        event: task_event.TaskEvent,
        worker_id: str,
    ) -> tuple[attempts.AttemptLease, process_outcome.ProcessOutcome]:
        lease = attempt_record.lease_from_record(
            attempt, attempt.active_worker_id or worker_id
        )
        return lease, self._reconciliation.terminal_outcome(
            session, task, attempt, event
        )

    def _scheduled_retry(
        self,
        task: workflow_db.TaskRecord,
        attempt: workflow_db.TaskAttemptRecord,
        event: task_event.TaskEvent,
        worker_id: str,
    ) -> tuple[attempts.AttemptLease, process_outcome.ProcessOutcome] | None:
        if attempt.next_attempt_at is None:
            return None
        retry_after = attempt_record.bounded_retry_delay(
            attempt.next_attempt_at,
            datetime_module.datetime.now(datetime_module.UTC),
            attempt.attempts_used,
        )
        if retry_after <= 0:
            attempt.next_attempt_at = None
            return None
        lease = attempt_record.lease_from_record(
            attempt, attempt.active_worker_id or worker_id
        )
        return lease, process_outcome.ProcessOutcome(
            task_id=event.task_id,
            event_id=event.event_id,
            status=task.status,
            outcome=ocr_outcome.OcrOutcome.TRANSIENT.value,
            attempt_number=attempt.attempts_used,
            retry_after_seconds=retry_after,
        )

    def _claim_budget(
        self,
        session: Any,
        task: workflow_db.TaskRecord,
        attempt: workflow_db.TaskAttemptRecord,
        event: task_event.TaskEvent,
        delivery: tuple[str, str],
    ) -> tuple[attempts.AttemptLease, process_outcome.ProcessOutcome | None]:
        now = datetime_module.datetime.now(datetime_module.UTC)
        worker_id, delivery_id = delivery
        try:
            next_budget, lease = attempt_record.budget_from_record(
                attempt, worker_id
            ).claim(worker_id, delivery_id=delivery_id)
        except attempts.AttemptBudgetExhaustedError:
            return self._mark_exhausted(
                session, task, attempt, event, worker_id
            )
        attempt.max_attempts = next_budget.max_attempts
        attempt.attempts_used = next_budget.attempts_used
        attempt.fencing_token = next_budget.fencing_token
        attempt.active_delivery_id = lease.delivery_id
        attempt.active_lease_id = lease.lease_id
        attempt.active_worker_id = lease.worker_id
        attempt.updated_at = now
        task.updated_at = now
        task.status = "processing"
        return lease, None

    def _mark_exhausted(
        self,
        session: Any,
        task: workflow_db.TaskRecord,
        attempt: workflow_db.TaskAttemptRecord,
        event: task_event.TaskEvent,
        worker_id: str,
    ) -> tuple[attempts.AttemptLease, process_outcome.ProcessOutcome]:
        lease = attempt_record.lease_from_record(attempt, worker_id)
        result_id, dead_letter_id = self._terminal_writer.write(
            session,
            task,
            attempt,
            event,
            lease,
            ocr_call_result.OcrCallResult(
                ocr_outcome.OcrOutcome.LIMIT,
                error="shared attempt budget exhausted",
            ),
            create_dead_letter=True,
        )
        return lease, process_outcome.ProcessOutcome(
            task_id=event.task_id,
            event_id=event.event_id,
            status=task.status,
            outcome=ocr_outcome.OcrOutcome.LIMIT.value,
            attempt_number=attempt.attempts_used,
            result_event_id=result_id,
            dead_letter_event_id=dead_letter_id,
        )
