from __future__ import annotations

import threading
import time
from typing import cast

import process_tests_assertions as checks
import process_tests_setup as support
from sird_workflow import db, ocr_call_result, ocr_outcome, task_event
from sird_workflow.process_outcome import ProcessOutcome
from sqlalchemy.engine import Engine


class BlockingOcr:
    def __init__(self) -> None:
        self.cancel_started = threading.Event()
        self.cancel_release = threading.Event()
        self.cancelled = threading.Event()
        self.finished = threading.Event()
        self.deadlines: list[float] = []

    def recognize(
        self, event: task_event.TaskEvent, *, deadline_seconds: float
    ) -> ocr_call_result.OcrCallResult:
        self.deadlines.append(deadline_seconds)
        self.cancelled.wait(timeout=support.WAIT_TIMEOUT_SECONDS)
        self.finished.set()
        return ocr_call_result.OcrCallResult(
            ocr_outcome.OcrOutcome.SUCCESS, {"text": "late"}
        )

    def cancel(self) -> None:
        self.cancel_started.set()
        self.cancel_release.wait(timeout=support.WAIT_TIMEOUT_SECONDS)
        self.cancelled.set()


def assert_task_status(
    engine: Engine, task_id: str, expected_status: str
) -> None:
    with db.session_factory(engine)() as session:
        task = cast(db.TaskRecord, session.get(db.TaskRecord, task_id))
        checks.check_present(task)
        checks.check_equal(task.status, expected_status)


def assert_blocking_outcome(
    outcome: ProcessOutcome, ocr: BlockingOcr, started_at: float
) -> None:
    checks.check_true(
        time.monotonic() - started_at < support.ELAPSED_LIMIT_SECONDS
    )
    checks.check_equal(outcome.status, "retrying")
    checks.check_equal(outcome.outcome, ocr_outcome.OcrOutcome.TRANSIENT.value)
    checks.check_absent(outcome.result_event_id)
    checks.check_true(
        ocr.cancel_started.wait(timeout=support.SIGNAL_TIMEOUT_SECONDS)
    )
    checks.check_false(ocr.cancelled.is_set())
    ocr.cancel_release.set()
    assert_blocking_completion(ocr)


def assert_blocking_completion(ocr: BlockingOcr) -> None:
    checks.check_true(
        ocr.cancelled.wait(timeout=support.SIGNAL_TIMEOUT_SECONDS)
    )
    checks.check_true(
        ocr.finished.wait(timeout=support.SIGNAL_TIMEOUT_SECONDS)
    )
    checks.check_equal(ocr.deadlines, [support.OCR_TIMEOUT_SECONDS])
