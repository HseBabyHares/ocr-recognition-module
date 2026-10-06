"""Completion transaction for OCR outcomes."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

import sird_workflow as workflow
from sird_workflow import (
    attempts,
    backoff,
    db,
    invalid_task_event_error,
    ocr_call_result,
    ocr_outcome,
    process_outcome,
    task_terminal_writer,
)

task_event = cast(Any, workflow).task_event

AttemptLease = attempts.AttemptLease
StaleAttemptLeaseError = attempts.StaleAttemptLeaseError
backoff_seconds = backoff.backoff_seconds
TaskAttemptRecord = db.TaskAttemptRecord
TaskRecord = db.TaskRecord
InvalidTaskEventError = invalid_task_event_error.InvalidTaskEventError
OcrCallResult = ocr_call_result.OcrCallResult
OcrOutcome = ocr_outcome.OcrOutcome
ProcessOutcome = process_outcome.ProcessOutcome
TaskEvent = task_event.TaskEvent
TaskTerminalWriter = task_terminal_writer.TaskTerminalWriter


@dataclass(frozen=True, slots=True)
class _CompletionContext:
    session: Session
    task: TaskRecord
    attempt: TaskAttemptRecord
    event: TaskEvent
    lease: AttemptLease
    ocr_result: OcrCallResult
    create_dead_letter: bool


def _write_terminal_outcome(
    writer: TaskTerminalWriter, context: _CompletionContext
) -> ProcessOutcome:
    result_id, dead_letter_id = writer.write(
        context.session,
        context.task,
        context.attempt,
        context.event,
        context.lease,
        context.ocr_result,
        create_dead_letter=context.create_dead_letter,
    )
    return ProcessOutcome(
        task_id=context.event.task_id,
        event_id=context.event.event_id,
        status=context.task.status,
        outcome=context.ocr_result.outcome.value,
        attempt_number=context.attempt.attempts_used,
        result_event_id=result_id,
        dead_letter_event_id=dead_letter_id,
    )


class TaskCompletion:
    """Own the transaction that fences and completes an OCR attempt."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        terminal_writer: TaskTerminalWriter,
    ) -> None:
        self._session_factory = session_factory
        self._terminal_writer = terminal_writer

    def complete(
        self,
        event: TaskEvent,
        delivery_id: str,
        lease: AttemptLease,
        ocr_result: OcrCallResult,
    ) -> ProcessOutcome:
        with self._session_factory() as session, session.begin():
            task, attempt = self._locked_records(session, event)
            self._validate_lease(attempt, delivery_id, lease, event)
            completion = self._normalize_result(
                task, attempt, event, ocr_result
            )
            if isinstance(completion[0], ProcessOutcome):
                return completion[0]
            context = _CompletionContext(
                session,
                task,
                attempt,
                event,
                lease,
                completion[0],
                completion[1],
            )
            return _write_terminal_outcome(self._terminal_writer, context)

    @classmethod
    def _normalize_result(
        cls,
        task: TaskRecord,
        attempt: TaskAttemptRecord,
        event: TaskEvent,
        ocr_result: OcrCallResult,
    ) -> tuple[OcrCallResult | ProcessOutcome, bool]:
        if ocr_result.outcome is not OcrOutcome.TRANSIENT:
            return ocr_result, False
        if ocr_result.requeue:
            return (
                cls._requeue_without_attempt(task, attempt, event, ocr_result),
                False,
            )
        retry = cls._retry_outcome(task, attempt, event, ocr_result)
        if retry is not None:
            return retry, False
        return (
            OcrCallResult(
                OcrOutcome.PERMANENT,
                result=ocr_result.payload,
                error=ocr_result.error,
            ),
            True,
        )

    @classmethod
    def _locked_records(
        cls, session: Session, event: TaskEvent
    ) -> tuple[TaskRecord, TaskAttemptRecord]:
        task = session.scalar(
            select(TaskRecord)
            .where(TaskRecord.task_id == event.task_id)
            .with_for_update()
        )
        attempt = session.scalar(
            select(TaskAttemptRecord)
            .where(TaskAttemptRecord.task_id == event.task_id)
            .with_for_update()
        )
        if task is None or attempt is None:
            raise InvalidTaskEventError("task attempt disappeared during OCR")
        return task, attempt

    @classmethod
    def _validate_lease(
        cls,
        attempt: TaskAttemptRecord,
        delivery_id: str,
        lease: AttemptLease,
        event: TaskEvent,
    ) -> None:
        lease_matches = (
            attempt.active_delivery_id == delivery_id
            and attempt.active_lease_id == lease.lease_id
            and attempt.fencing_token == lease.fencing_token
            and attempt.terminal_outcome is None
        )
        if not lease_matches:
            raise StaleAttemptLeaseError(
                f"lease {lease.lease_id!r} is stale for task {event.task_id!r}"
            )

    @classmethod
    def _requeue_without_attempt(
        cls,
        task: TaskRecord,
        attempt: TaskAttemptRecord,
        event: TaskEvent,
        ocr_result: OcrCallResult,
    ) -> ProcessOutcome:
        now = datetime.now(UTC)
        task.status = "retrying"
        task.updated_at = now
        attempt.attempts_used = max(0, attempt.attempts_used - 1)
        attempt.next_attempt_at = None
        attempt.active_delivery_id = None
        attempt.active_lease_id = None
        attempt.active_worker_id = None
        attempt.updated_at = now
        return ProcessOutcome(
            task_id=event.task_id,
            event_id=event.event_id,
            status=task.status,
            outcome=ocr_result.outcome.value,
            attempt_number=attempt.attempts_used,
            retry_after_seconds=0,
        )

    @classmethod
    def _retry_outcome(
        cls,
        task: TaskRecord,
        attempt: TaskAttemptRecord,
        event: TaskEvent,
        ocr_result: OcrCallResult,
    ) -> ProcessOutcome | None:
        if attempt.attempts_used >= attempt.max_attempts:
            return None
        now = datetime.now(UTC)
        retry_after = backoff_seconds(attempt.attempts_used)
        task.status = "retrying"
        task.updated_at = now
        attempt.next_attempt_at = now + timedelta(seconds=retry_after)
        attempt.active_delivery_id = None
        attempt.active_lease_id = None
        attempt.active_worker_id = None
        attempt.updated_at = now
        return ProcessOutcome(
            task_id=event.task_id,
            event_id=event.event_id,
            status=task.status,
            outcome=ocr_result.outcome.value,
            attempt_number=attempt.attempts_used,
            retry_after_seconds=retry_after,
        )
