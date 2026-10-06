"""Read and validate terminal task outcomes."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from sird_workflow.db import (
    TaskAttemptRecord,
    TaskDeadLetterOutbox,
    TaskRecord,
    TaskResultOutbox,
)
from sird_workflow.event_record_validation import validate_event_against_task
from sird_workflow.invalid_task_event_error import InvalidTaskEventError
from sird_workflow.process_outcome import ProcessOutcome
from sird_workflow.task_event import TaskEvent


class TaskReconciliation:
    """Reconcile a decoded event against durable terminal records."""

    def reconcile(
        self,
        session: Session,
        event: TaskEvent,
    ) -> ProcessOutcome | None:
        task = session.scalar(
            select(TaskRecord).where(TaskRecord.task_id == event.task_id)
        )
        attempt = session.scalar(
            select(TaskAttemptRecord).where(
                TaskAttemptRecord.task_id == event.task_id
            )
        )
        if task is None or attempt is None:
            raise InvalidTaskEventError(
                f"task {event.task_id!r} does not exist"
            )
        validate_event_against_task(task, event)
        if attempt.max_attempts != event.max_attempts:
            raise InvalidTaskEventError(
                "task event attempt budget does not match durable state"
            )
        if attempt.terminal_outcome is None:
            return None
        return self.terminal_outcome(session, task, attempt, event)

    def terminal_outcome(
        self,
        session: Session,
        task: TaskRecord,
        attempt: TaskAttemptRecord,
        event: TaskEvent,
    ) -> ProcessOutcome:
        result_id = f"{event.event_id}:result"
        result_outbox = session.scalar(
            select(TaskResultOutbox).where(
                TaskResultOutbox.event_id == result_id
            )
        )
        if not self._result_matches(result_outbox, result_id, attempt, event):
            raise InvalidTaskEventError(
                "terminal result identity does not match source event"
            )

        expected_dead_letter_id = f"{event.event_id}:dead-letter"
        dead_letter = session.scalar(
            select(TaskDeadLetterOutbox).where(
                TaskDeadLetterOutbox.event_id == expected_dead_letter_id
            )
        )
        dead_letter_id = None
        if dead_letter is not None:
            if not self._dead_letter_matches(
                dead_letter, expected_dead_letter_id, event
            ):
                raise InvalidTaskEventError(
                    "dead-letter identity does not match source event"
                )
            dead_letter_id = expected_dead_letter_id
        return ProcessOutcome(
            task_id=event.task_id,
            event_id=event.event_id,
            status=task.status,
            outcome=self._require_terminal_outcome(attempt.terminal_outcome),
            attempt_number=attempt.attempts_used,
            result_event_id=result_id,
            dead_letter_event_id=dead_letter_id,
        )

    def _require_terminal_outcome(cls, outcome: str | None) -> str:
        if outcome is None:
            raise InvalidTaskEventError(
                "terminal outcome is missing from durable attempt state"
            )
        return outcome

    @classmethod
    def _result_matches(
        cls,
        result_outbox: TaskResultOutbox | None,
        result_id: str,
        attempt: TaskAttemptRecord,
        event: TaskEvent,
    ) -> bool:
        if result_outbox is None:
            return False
        return all(
            (
                result_outbox.task_id == event.task_id,
                result_outbox.source_event_id == event.event_id,
                result_outbox.request_id == event.request_id,
                result_outbox.payload.get("event_id") == result_id,
                result_outbox.payload.get("task_id") == event.task_id,
                result_outbox.payload.get("request_id") == event.request_id,
                attempt.terminal_result_id == result_id,
            )
        )

    @classmethod
    def _dead_letter_matches(
        cls,
        dead_letter: TaskDeadLetterOutbox,
        expected_id: str,
        event: TaskEvent,
    ) -> bool:
        return all(
            (
                dead_letter.task_id == event.task_id,
                dead_letter.source_event_id == event.event_id,
                dead_letter.request_id == event.request_id,
                dead_letter.payload.get("event_id") == expected_id,
                dead_letter.payload.get("task_id") == event.task_id,
                dead_letter.payload.get("request_id") == event.request_id,
            )
        )
