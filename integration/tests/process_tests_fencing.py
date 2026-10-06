from __future__ import annotations

from typing import cast

import process_tests_assertions as checks
import process_tests_setup as support
import pytest
import sqlalchemy
from sird_workflow import (
    attempts,
    db,
    invalid_task_event_error,
    ocr_call_result,
    ocr_outcome,
    process,
    task_event,
)
from sqlalchemy.engine import Engine


class TakeoverOcr:
    def __init__(self) -> None:
        self.service: process.ProcessService | None = None
        self.taken_over = False

    def recognize(
        self, event: task_event.TaskEvent, *, deadline_seconds: float
    ) -> ocr_call_result.OcrCallResult:
        if not self.taken_over:
            self.taken_over = True
            checks.check_present(self.service)
            outcome = cast(process.ProcessService, self.service).process_event(
                event, "worker-b", "delivery-a"
            )
            checks.check_equal(outcome.status, "succeeded")
        return ocr_call_result.OcrCallResult(
            ocr_outcome.OcrOutcome.SUCCESS, {"text": "ok"}
        )


def _make_takeover_case() -> tuple[
    task_event.TaskEvent,
    TakeoverOcr,
    process.ProcessService,
    Engine,
]:
    event = support.make_event()
    ocr = TakeoverOcr()
    service, engine = support.make_service(event, ocr)
    ocr.service = service
    return event, ocr, service, engine


def _assert_active_worker(engine: Engine, task_id: str) -> None:
    with db.session_factory(engine)() as session:
        attempt = cast(
            db.TaskAttemptRecord,
            session.get(db.TaskAttemptRecord, task_id),
        )
        checks.check_present(attempt)
        checks.check_equal(attempt.active_worker_id, "worker-b")


def _assert_single_outbox(engine: Engine) -> None:
    with db.session_factory(engine)() as session:
        count = session.scalar(
            sqlalchemy.select(sqlalchemy.func.count()).select_from(
                db.TaskResultOutbox
            )
        )
        checks.check_equal(count, 1)


def test_decode_rejects_version() -> None:
    with pytest.raises(invalid_task_event_error.InvalidTaskEventError):
        task_event.TaskEvent.decode({"event_type": "sird.task.submitted.v2"})


def test_stale_completion_rejected() -> None:
    event, _ocr, service, engine = _make_takeover_case()

    with pytest.raises(attempts.StaleAttemptLeaseError):
        service.process_event(event, "worker-a", "delivery-a")

    _assert_active_worker(engine, event.task_id)


def test_reconcile_rejects_divergence() -> None:
    event = support.make_event()
    service, engine = support.make_service(event, support.SuccessOcr())
    service.process_event(event, "worker-a", "delivery-a")
    divergent = task_event.TaskEvent(
        event_id="submitted-other",
        task_id=event.task_id,
        request_id=event.request_id,
        artifact_ref=event.artifact_ref,
        policy=event.policy,
        retention_seconds=event.retention_seconds,
        max_attempts=event.max_attempts,
        submitted_at=event.submitted_at,
        retention_expires_at=event.retention_expires_at,
    )

    with pytest.raises(invalid_task_event_error.InvalidTaskEventError):
        service.reconcile_event(divergent)

    _assert_single_outbox(engine)
