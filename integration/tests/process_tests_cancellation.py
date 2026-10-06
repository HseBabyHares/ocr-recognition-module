import functools
import threading
import time
from typing import cast

import process_tests_assertions as checks
import process_tests_cancellation_support as cancellation_checks
import process_tests_setup as support
import pytest
from sird_workflow import (
    cancellation,
    db,
    ocr_call_result,
    ocr_outcome,
    task_event,
)
from sird_workflow.process_outcome import ProcessOutcome
from sqlalchemy import select
from sqlalchemy.engine import Engine


class CancellationCase:
    def __init__(self, max_attempts: int = 2) -> None:
        self._event = support.make_event(max_attempts=max_attempts)
        self._cancellation = cancellation.CancellationToken()
        self._started = threading.Event()
        self._release = threading.Event()
        service, engine = support.make_service(
            self._event,
            CancellableOcr(self._started, self._release),
        )
        self.service = service
        self.engine = engine
        self._outcomes: list[ProcessOutcome] = []
        call = functools.partial(
            self.service.process_event,
            self._event,
            "worker-a",
            "delivery-a",
            self._cancellation,
        )
        self.worker = threading.Thread(
            target=functools.partial(
                checks.append_call_result, self._outcomes, call
            )
        )

    def start(self) -> None:
        self.worker.start()
        checks.check_true(
            self._started.wait(timeout=support.SIGNAL_TIMEOUT_SECONDS)
        )

    def finish(self) -> None:
        self.worker.join(timeout=support.SIGNAL_TIMEOUT_SECONDS)
        checks.check_false(self.worker.is_alive())


class CancellableOcr:
    def __init__(
        self, started: threading.Event, release: threading.Event
    ) -> None:
        self.started = started
        self.release = release

    def recognize(
        self, event: task_event.TaskEvent, *, deadline_seconds: float
    ) -> ocr_call_result.OcrCallResult:
        self.started.set()
        self.release.wait(timeout=support.WAIT_TIMEOUT_SECONDS)
        return ocr_call_result.OcrCallResult(
            ocr_outcome.OcrOutcome.SUCCESS, {"late": True}
        )

    def cancel(self) -> None:
        self.release.set()


def test_blocking_ocr_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        support.process_module,
        "OCR_DEADLINE_SECONDS",
        support.OCR_TIMEOUT_SECONDS,
    )
    event = support.make_event()
    ocr = cancellation_checks.BlockingOcr()
    service = support.make_service(event, ocr)[0]

    started_at = time.monotonic()
    outcome = service.process_event(event, "worker-a", "delivery-a")
    cancellation_checks.assert_blocking_outcome(outcome, ocr, started_at)


def _complete_then_cancel() -> tuple[
    ProcessOutcome, Engine, task_event.TaskEvent
]:
    event = support.make_event()
    cancellation_token = cancellation.CancellationToken()
    service, engine = support.make_service(event, support.FastOcr())
    outcome = service.process_event(
        event,
        "worker-a",
        "delivery-a",
        cancellation_token,
    )
    cancellation_token.cancel()
    return outcome, engine, event


def test_caller_cancel_terminal() -> None:
    case = CancellationCase()
    case.start()
    case._cancellation.cancel()
    case.finish()

    outcome = case._outcomes[0]
    checks.check_equal(outcome.outcome, ocr_outcome.OcrOutcome.CANCELLED.value)
    checks.check_equal(outcome.status, "cancelled")
    checks.check_true(outcome.terminal)
    cancellation_checks.assert_task_status(
        case.engine, case._event.task_id, "cancelled"
    )


def test_nonterminal_cancel_requeues() -> None:
    case = CancellationCase(max_attempts=1)
    case.start()
    case._cancellation.cancel(terminal=False)
    case.finish()

    outcome = case._outcomes[0]
    checks.check_equal(outcome.outcome, ocr_outcome.OcrOutcome.TRANSIENT.value)
    checks.check_false(outcome.terminal)
    with db.session_factory(case.engine)() as session:
        attempt = cast(
            db.TaskAttemptRecord,
            session.get(db.TaskAttemptRecord, case._event.task_id),
        )
        checks.check_present(attempt)
        checks.check_equal(attempt.attempts_used, 0)
        checks.check_absent(session.scalar(select(db.TaskResultOutbox)))
    cancellation_checks.assert_task_status(
        case.engine, case._event.task_id, "retrying"
    )


def test_cancel_after_completion() -> None:
    outcome, engine, event = _complete_then_cancel()

    checks.check_equal(outcome.outcome, ocr_outcome.OcrOutcome.SUCCESS.value)
    checks.check_true(outcome.terminal)
    cancellation_checks.assert_task_status(engine, event.task_id, "succeeded")
