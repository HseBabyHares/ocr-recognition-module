from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sird_workflow.db import TaskRecord, TaskResultOutbox, session_factory
from sird_workflow.models import DEFAULT_RETENTION_SECONDS, SubmitRequest
from sird_workflow.service import WorkflowService
from sqlalchemy.engine import Engine


def assert_expired(
    service: WorkflowService, backend: str, task_id: str
) -> None:
    response = service.get_result(backend, task_id)
    assert response.expired is True
    assert getattr(response, "result", None) is None


def assert_cleanup(
    service: WorkflowService,
    engine: Engine,
    request: SubmitRequest,
    backend: str,
) -> None:
    service.submit(backend, request)
    expiry = datetime.now(UTC) - timedelta(seconds=1)
    with session_factory(engine)() as session, session.begin():
        task = session.get(TaskRecord, request.task_id)
        assert task is not None
        task.status = "succeeded"
        task.result_payload = {"fields": {"snils": "redacted-test-value"}}
        task.retention_expires_at = expiry
        session.add(
            TaskResultOutbox(
                event_id="task-3:result",
                task_id=request.task_id,
                source_event_id="submitted-3",
                request_id=request.request_id,
                topic="sird.result.v1",
                payload={"result": getattr(task, "result", None)},
                created_at=expiry,
            )
        )
    assert service.purge_expired_results(now=datetime.now(UTC)) == 1
    assert_suppressed_outbox(engine)
    assert service.purge_expired_results(now=datetime.now(UTC)) == 0


def assert_suppressed_outbox(engine: Engine) -> None:
    with session_factory(engine)() as session:
        outbox = session.get(TaskResultOutbox, "task-3:result")
        assert outbox is not None
        assert outbox.suppressed_at is not None
        assert outbox.suppression_reason == "retention_expired"


def assert_retention_record(
    engine: Engine, request: SubmitRequest, seconds: int
) -> None:
    with session_factory(engine)() as session:
        task = session.get(TaskRecord, request.task_id)
        assert task is not None
        assert task.retention_seconds == DEFAULT_RETENTION_SECONDS == seconds
        assert (
            task.retention_expires_at - task.created_at
        ).total_seconds() == DEFAULT_RETENTION_SECONDS
