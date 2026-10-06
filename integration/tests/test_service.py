from datetime import UTC, datetime, timedelta

import pytest
from service_tests_support import (
    assert_cleanup,
    assert_expired,
    assert_retention_record,
)
from sird_workflow.db import TaskRecord, session_factory
from sird_workflow.exceptions import InvalidIdempotentReuseError
from sird_workflow.models import DEFAULT_RETENTION_SECONDS, SubmitRequest
from sqlalchemy import update
from test_service_support import (
    BACKEND,
    CAPABILITY,
    RETENTION_SECONDS,
    service,
)


def test_submit_idempotent_event() -> None:
    workflow, producer = service()[:2]
    request = SubmitRequest(
        task_id="task-1",
        request_id="request-1",
        artifact_ref=CAPABILITY,
        policy={"mode": "strict"},
    )
    first = workflow.submit(BACKEND, request)
    second = workflow.submit(BACKEND, request)
    assert first.task_id == second.task_id
    assert len(producer.events) == 1
    with pytest.raises(InvalidIdempotentReuseError):
        workflow.submit(
            BACKEND,
            SubmitRequest(
                task_id="task-1",
                request_id="request-1",
                artifact_ref="v1.other",
                policy={"mode": "strict"},
            ),
        )


def test_submit_uses_retention_fallback() -> None:
    workflow, _producer, engine = service()
    request = SubmitRequest(
        task_id="task-retention",
        request_id="request-retention",
        artifact_ref=CAPABILITY,
    )
    submission = workflow.submit(BACKEND, request)
    assert_retention_record(engine, request, RETENTION_SECONDS)
    assert (
        submission.retention_expires_at - submission.submitted_at
    ).total_seconds() == DEFAULT_RETENTION_SECONDS


def test_result_payload_hidden_after_expiry() -> None:
    workflow, _producer, engine = service()
    request = SubmitRequest(
        task_id="task-2", request_id="request-2", artifact_ref=CAPABILITY
    )
    workflow.submit(BACKEND, request)
    with session_factory(engine)() as session, session.begin():
        session.execute(
            update(TaskRecord)
            .where(TaskRecord.task_id == request.task_id)
            .values(
                status="succeeded",
                result={"fields": {"snils": "redacted-test-value"}},
                retention_expires_at=datetime.now(UTC) - timedelta(seconds=1),
            )
        )
    assert_expired(workflow, BACKEND, request.task_id)


def test_expired_cleanup() -> None:
    workflow, _producer, engine = service()
    request = SubmitRequest(
        task_id="task-3", request_id="request-3", artifact_ref=CAPABILITY
    )
    assert_cleanup(workflow, engine, request, BACKEND)
    assert_expired(workflow, BACKEND, request.task_id)
