"""Write terminal task state and outbox records in a caller transaction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from sird_workflow.attempt_record import budget_from_record
from sird_workflow.attempts import AttemptLease
from sird_workflow.db import (
    TaskAttemptRecord,
    TaskDeadLetterOutbox,
    TaskRecord,
    TaskResultOutbox,
)
from sird_workflow.ocr_call_result import OcrCallResult
from sird_workflow.ocr_outcome import OcrOutcome
from sird_workflow.task_event import TaskEvent

RESULT_EVENT_TYPE = "sird.task.result.v1"
DEAD_LETTER_EVENT_TYPE = "sird.task.dead-letter.v1"


@dataclass(frozen=True, slots=True)
class _TerminalWriteArguments:
    event: TaskEvent
    lease: AttemptLease
    ocr_result: OcrCallResult
    create_dead_letter: bool


class _TerminalWriteResolver:
    @classmethod
    def resolve(
        cls, write_args: tuple[Any, ...], write_options: dict[str, Any]
    ) -> _TerminalWriteArguments:
        arguments = cls._merge(write_args, write_options)
        resolved = _TerminalWriteArguments(
            event=cls._required(arguments, "event"),
            lease=cls._required(arguments, "lease"),
            ocr_result=cls._required(arguments, "ocr_result"),
            create_dead_letter=arguments.get("create_dead_letter", False),
        )
        unexpected = set(arguments) - {
            "event",
            "lease",
            "ocr_result",
            "create_dead_letter",
        }
        if unexpected:
            raise TypeError(
                f"unexpected terminal writer argument: "
                f"{next(iter(unexpected))!r}"
            )
        return resolved

    @classmethod
    def _merge(
        cls, write_args: tuple[Any, ...], write_options: dict[str, Any]
    ) -> dict[str, Any]:
        names = ("event", "lease", "ocr_result")
        if len(write_args) > len(names):
            raise TypeError("too many terminal writer arguments")
        resolved = dict(zip(names, write_args, strict=True))
        overlap = resolved.keys() & write_options.keys()
        if overlap:
            raise TypeError(f"multiple values for {next(iter(overlap))!r}")
        resolved.update(write_options)
        return resolved

    @classmethod
    def _required(cls, arguments: dict[str, Any], name: str) -> Any:
        if name not in arguments:
            raise TypeError("missing terminal writer argument")
        return arguments[name]


def _result_payload(
    result_id: str, event: TaskEvent, ocr_result: OcrCallResult
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event_id": result_id,
        "event_type": RESULT_EVENT_TYPE,
        "task_id": event.task_id,
        "request_id": event.request_id,
        "outcome": ocr_result.outcome.value,
        "result": dict(ocr_result.payload or {}),
    }
    if ocr_result.error is not None:
        payload["error"] = ocr_result.error
    return payload


def _dead_letter_payload(
    dead_letter_id: str, event: TaskEvent, ocr_result: OcrCallResult
) -> dict[str, Any]:
    return {
        "event_id": dead_letter_id,
        "event_type": DEAD_LETTER_EVENT_TYPE,
        "task_id": event.task_id,
        "request_id": event.request_id,
        "source_event_id": event.event_id,
        "reason": ocr_result.error or "attempt budget exhausted",
    }


class TaskTerminalWriter:
    """Persist terminal state and result/dead-letter outboxes atomically."""

    def __init__(self, result_topic: str, dead_letter_topic: str) -> None:
        self._result_topic = result_topic
        self._dead_letter_topic = dead_letter_topic

    def write(
        self,
        session: Session,
        task: TaskRecord,
        attempt: TaskAttemptRecord,
        *write_args: Any,
        **write_options: Any,
    ) -> tuple[str, str | None]:
        arguments = _TerminalWriteResolver.resolve(write_args, write_options)
        return self._write_terminal_records(session, task, attempt, arguments)

    def _write_terminal_records(
        self,
        session: Session,
        task: TaskRecord,
        attempt: TaskAttemptRecord,
        arguments: _TerminalWriteArguments,
    ) -> tuple[str, str | None]:
        event_id = arguments.event.event_id
        result_id = f"{event_id}:result"
        self._update_terminal_state(
            task,
            attempt,
            arguments.event,
            arguments.lease,
            arguments.ocr_result,
        )
        self._write_result_outbox(
            session,
            arguments.event,
            result_id,
            _result_payload(result_id, arguments.event, arguments.ocr_result),
        )
        if not arguments.create_dead_letter:
            return result_id, None
        dead_letter_id = f"{event_id}:dead-letter"
        self._write_dead_letter_outbox(
            session,
            arguments.event,
            dead_letter_id,
            _dead_letter_payload(
                dead_letter_id, arguments.event, arguments.ocr_result
            ),
        )
        return result_id, dead_letter_id

    @classmethod
    def _update_terminal_state(
        cls,
        task: TaskRecord,
        attempt: TaskAttemptRecord,
        event: TaskEvent,
        lease: AttemptLease,
        ocr_result: OcrCallResult,
    ) -> None:
        outcome = ocr_result.outcome
        task.status = {
            OcrOutcome.SUCCESS: "succeeded",
            OcrOutcome.REJECTED: "rejected",
            OcrOutcome.PERMANENT: "failed",
            OcrOutcome.CANCELLED: "cancelled",
            OcrOutcome.LIMIT: "limit",
        }[outcome]
        task.result_payload = dict(ocr_result.payload or {})
        task.updated_at = datetime.now(UTC)
        budget = budget_from_record(attempt, lease.worker_id)
        if budget.active_lease is None:
            attempt.terminal_outcome = outcome.value
            attempt.terminal_result_id = f"{event.event_id}:result"
        else:
            completed_budget = budget.complete(
                lease,
                outcome=outcome.value,
                result_id=f"{event.event_id}:result",
            )
            attempt.terminal_outcome = completed_budget.terminal_outcome
            attempt.terminal_result_id = completed_budget.terminal_result_id
        attempt.next_attempt_at = None
        attempt.updated_at = datetime.now(UTC)

    def _write_result_outbox(
        self,
        session: Session,
        event: TaskEvent,
        result_id: str,
        payload: dict[str, Any],
    ) -> None:
        if (
            session.scalar(
                select(TaskResultOutbox).where(
                    TaskResultOutbox.event_id == result_id
                )
            )
            is None
        ):
            session.add(
                TaskResultOutbox(
                    event_id=result_id,
                    task_id=event.task_id,
                    source_event_id=event.event_id,
                    request_id=event.request_id,
                    topic=self._result_topic,
                    payload=payload,
                    created_at=datetime.now(UTC),
                )
            )

    def _write_dead_letter_outbox(
        self,
        session: Session,
        event: TaskEvent,
        dead_letter_id: str,
        payload: dict[str, Any],
    ) -> None:
        if (
            session.scalar(
                select(TaskDeadLetterOutbox).where(
                    TaskDeadLetterOutbox.event_id == dead_letter_id
                )
            )
            is None
        ):
            session.add(
                TaskDeadLetterOutbox(
                    event_id=dead_letter_id,
                    task_id=event.task_id,
                    source_event_id=event.event_id,
                    request_id=event.request_id,
                    topic=self._dead_letter_topic,
                    payload=payload,
                    created_at=datetime.now(UTC),
                )
            )
