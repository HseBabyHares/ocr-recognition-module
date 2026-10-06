from __future__ import annotations

import process_tests_policy_support as fixtures
from process_tests_assertions import check_equal, check_true
from sird_workflow import ocr_executor as process_module
from sird_workflow.db import TaskAttemptRecord, session_factory
from sird_workflow.ocr_outcome import OcrOutcome


def test_grpc_retry_policy() -> None:
    unavailable = process_module._classify_ocr_exception(
        fixtures.GrpcStyleError(fixtures.GrpcStatus.UNAVAILABLE)
    )
    deadline = process_module._classify_ocr_exception(
        fixtures.GrpcStyleError("StatusCode.DEADLINE_EXCEEDED")
    )
    exhausted = process_module._classify_ocr_exception(
        fixtures.GrpcStyleError("StatusCode.RESOURCE_EXHAUSTED")
    )
    cancelled = process_module._classify_ocr_exception(
        fixtures.GrpcStyleError(fixtures.GrpcStatus.CANCELLED, retryable=True)
    )

    check_equal(unavailable.outcome, OcrOutcome.TRANSIENT)
    check_equal(deadline.outcome, OcrOutcome.TRANSIENT)
    check_equal(exhausted.outcome, OcrOutcome.PERMANENT)
    check_equal(cancelled.outcome, OcrOutcome.CANCELLED)


def test_adapter_retryable_fallback() -> None:
    outcome = process_module._classify_ocr_exception(fixtures.AdapterError())
    check_equal(outcome.outcome, OcrOutcome.TRANSIENT)


def test_client_requeue_spends_budget() -> None:
    outcome, engine, event = fixtures.run_client_requeue()

    check_equal(outcome.outcome, OcrOutcome.TRANSIENT.value)

    with session_factory(engine)() as session:
        attempt = session.get(TaskAttemptRecord, event.task_id)
        assert attempt is not None
        check_equal(attempt.attempts_used, 1)
        check_true(attempt.next_attempt_at is not None)
