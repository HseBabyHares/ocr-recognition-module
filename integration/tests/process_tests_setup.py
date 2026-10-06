from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import sird_workflow as workflow
from process_tests_sqlite import make_engine
from sird_workflow import (
    db,
    identity,
    models,
    ocr_call_result,
    ocr_client,
    ocr_executor,
    ocr_outcome,
    process,
)
from sqlalchemy.engine import Engine

task_event = cast(Any, workflow).task_event

RETENTION_SECONDS = 3600
WAIT_TIMEOUT_SECONDS = 2.0
SIGNAL_TIMEOUT_SECONDS = 1.0
OCR_TIMEOUT_SECONDS = 0.05
ELAPSED_LIMIT_SECONDS = 0.5
RETRY_AFTER_SECONDS = 1.0
SUCCESS_DEADLINE_SECONDS = 35.0
ZERO_SECONDS = 0
process_module = ocr_executor


def make_event(max_attempts: int = 2) -> task_event.TaskEvent:
    now = datetime.now(UTC)
    return task_event.TaskEvent(
        event_id="submitted-1",
        task_id="task-1",
        request_id="request-1",
        artifact_ref="artifact-1",
        policy={},
        retention_seconds=RETENTION_SECONDS,
        max_attempts=max_attempts,
        submitted_at=now,
        retention_expires_at=now + timedelta(hours=1),
    )


def make_service(
    event: task_event.TaskEvent, ocr: ocr_client.OcrClient
) -> tuple[process.ProcessService, Engine]:
    engine = make_engine()
    db.create_schema(engine)
    now = datetime.now(UTC)
    request = models.SubmitRequest(
        task_id=event.task_id,
        request_id=event.request_id,
        artifact_ref=event.artifact_ref,
        policy=event.policy,
        retention_seconds=event.retention_seconds,
    )
    with db.session_factory(engine)() as session, session.begin():
        session.add(
            db.TaskRecord(
                task_id=event.task_id,
                request_id=event.request_id,
                artifact_ref=event.artifact_ref,
                policy={},
                request_fingerprint=identity.request_fingerprint(request),
                status="queued",
                retention_seconds=event.retention_seconds,
                retention_expires_at=event.retention_expires_at,
                created_at=event.submitted_at,
                updated_at=event.submitted_at,
            )
        )
        session.add(
            db.TaskAttemptRecord(
                task_id=event.task_id,
                max_attempts=event.max_attempts,
                updated_at=now,
            )
        )
    return process.ProcessService(engine, ocr), engine


class SuccessOcr:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def recognize(
        self, event: task_event.TaskEvent, *, deadline_seconds: float
    ) -> ocr_call_result.OcrCallResult:
        self.calls.append(deadline_seconds)
        return ocr_call_result.OcrCallResult(
            ocr_outcome.OcrOutcome.SUCCESS, {"text": "ok"}
        )


class FastOcr:
    def recognize(
        self, event: task_event.TaskEvent, *, deadline_seconds: float
    ) -> ocr_call_result.OcrCallResult:
        return ocr_call_result.OcrCallResult(
            ocr_outcome.OcrOutcome.SUCCESS, {"text": "complete"}
        )
