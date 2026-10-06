from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

import process_tests_assertions as checks
import process_tests_setup as support
import sqlalchemy
from sird_workflow import db, ocr_call_result, ocr_outcome, task_event
from sird_workflow.process_outcome import ProcessOutcome
from sqlalchemy.engine import Engine

WORKER_ID = "worker-a"
DELIVERY_A = "delivery-a"
DELIVERY_B = "delivery-b"
DELIVERY_C = "delivery-c"


class TransientOcr:
    def recognize(
        self, event: task_event.TaskEvent, *, deadline_seconds: float
    ) -> ocr_call_result.OcrCallResult:
        return ocr_call_result.OcrCallResult(
            ocr_outcome.OcrOutcome.TRANSIENT, error="temporary"
        )


class SuccessCase:
    def __init__(self) -> None:
        self.event = support.make_event()
        self.ocr = support.SuccessOcr()
        service_data = support.make_service(self.event, self.ocr)
        self.service = service_data[0]
        self.engine: Engine = service_data[1]

    def check_fenced_duplicate(self) -> None:
        first = self.service.process_event(self.event, WORKER_ID, DELIVERY_A)
        second = self.service.process_event(self.event, WORKER_ID, DELIVERY_A)

        checks.check_equal(first.status, "succeeded")
        checks.check_equal(first.result_event_id, "submitted-1:result")
        checks.check_equal(second.result_event_id, first.result_event_id)
        checks.check_equal(self.ocr.calls, [support.SUCCESS_DEADLINE_SECONDS])
        with db.session_factory(self.engine)() as session:
            count = session.scalar(
                sqlalchemy.select(sqlalchemy.func.count()).select_from(
                    db.TaskResultOutbox
                )
            )
            checks.check_equal(count, 1)

    def check_reconcile(self) -> None:
        self.service.process_event(self.event, WORKER_ID, DELIVERY_A)
        reconciled = self.service.reconcile_event(self.event)
        reconciled = cast(ProcessOutcome, reconciled)
        checks.check_present(reconciled)
        checks.check_equal(reconciled.result_event_id, "submitted-1:result")
        checks.check_equal(self.ocr.calls, [support.SUCCESS_DEADLINE_SECONDS])


class RetryCase:
    def __init__(self) -> None:
        self.event = support.make_event(max_attempts=2)
        service_data = support.make_service(self.event, TransientOcr())
        self.service = service_data[0]
        self.engine: Engine = service_data[1]

    def process(self, delivery_id: str) -> ProcessOutcome:
        return self.service.process_event(self.event, WORKER_ID, delivery_id)

    def check_first_schedule(self) -> ProcessOutcome:
        retry = self.process(DELIVERY_A)
        with db.session_factory(self.engine)() as session:
            attempt = cast(
                db.TaskAttemptRecord,
                session.get(db.TaskAttemptRecord, self.event.task_id),
            )
            checks.check_present(attempt)
            next_attempt_at = cast(datetime, attempt.next_attempt_at)
            scheduled_at = (
                next_attempt_at.replace(tzinfo=UTC)
                if next_attempt_at.tzinfo is None
                else next_attempt_at
            )
            checks.check_greater(scheduled_at, datetime.now(UTC))
        return retry

    def check_immediate(self) -> ProcessOutcome:
        immediate = self.process(DELIVERY_B)
        with db.session_factory(self.engine)() as session:
            attempt = cast(
                db.TaskAttemptRecord,
                session.get(db.TaskAttemptRecord, self.event.task_id),
            )
            checks.check_present(attempt)
            checks.check_equal(attempt.attempts_used, 1)
            checks.check_present(attempt.next_attempt_at)
        return immediate

    def check_terminal(self) -> ProcessOutcome:
        with db.session_factory(self.engine)() as session, session.begin():
            attempt = cast(
                db.TaskAttemptRecord,
                session.get(db.TaskAttemptRecord, self.event.task_id),
            )
            checks.check_present(attempt)
            attempt.next_attempt_at = datetime.now(UTC) - timedelta(
                seconds=support.RETRY_AFTER_SECONDS
            )
        return self.process(DELIVERY_C)

    def _verify_outcomes(
        self,
        retry: ProcessOutcome,
        immediate: ProcessOutcome,
        terminal: ProcessOutcome,
    ) -> None:
        checks.check_equal(retry.status, "retrying")
        checks.check_equal(
            retry.retry_after_seconds, support.RETRY_AFTER_SECONDS
        )
        checks.check_absent(retry.result_event_id)
        checks.check_equal(immediate.status, "retrying")
        checks.check_greater(
            immediate.retry_after_seconds, support.ZERO_SECONDS
        )
        checks.check_absent(immediate.result_event_id)
        checks.check_equal(terminal.status, "failed")
        checks.check_equal(
            terminal.dead_letter_event_id, "submitted-1:dead-letter"
        )

    def _verify_terminal_records(self) -> None:
        with db.session_factory(self.engine)() as session:
            attempt = cast(
                db.TaskAttemptRecord,
                session.get(db.TaskAttemptRecord, self.event.task_id),
            )
            checks.check_present(attempt)
            checks.check_equal(attempt.attempts_used, 2)
            checks.check_absent(attempt.next_attempt_at)
            count = session.scalar(
                sqlalchemy.select(sqlalchemy.func.count()).select_from(
                    db.TaskResultOutbox
                )
            )
            checks.check_equal(count, 1)
            dead_letter = cast(
                db.TaskDeadLetterOutbox,
                session.scalar(sqlalchemy.select(db.TaskDeadLetterOutbox)),
            )
            checks.check_present(dead_letter)
            checks.check_absent(dead_letter.acknowledged_at)


def test_success_fenced_duplicate() -> None:
    SuccessCase().check_fenced_duplicate()


def test_reconcile_reads_result() -> None:
    SuccessCase().check_reconcile()


def test_retry_schedule_redelivery() -> None:
    retry_case = RetryCase()
    retry = retry_case.check_first_schedule()
    immediate = retry_case.check_immediate()
    terminal = retry_case.check_terminal()
    retry_case._verify_outcomes(retry, immediate, terminal)
    retry_case._verify_terminal_records()
