from datetime import datetime

import pytest
from sird_workflow.config import WorkflowConfig
from sird_workflow.identity import request_fingerprint, task_event_payload
from sird_workflow.models import DEFAULT_RETENTION_SECONDS, SubmitRequest
from sird_workflow.producer import RabbitMQProducerConfig

TASK_ID = "task-1"
REQUEST_ID = "request-1"
ARTIFACT = "v1.one"
MODE = "mode"
STRICT = "strict"
EVENT_TIME = datetime.fromisoformat("2026-01-01T00:00:00+00:00")
EVENT_EXPIRY = datetime.fromisoformat("2026-01-01T12:00:00+00:00")


def test_stable_fingerprint_for_identical_request() -> None:
    first = SubmitRequest(
        task_id=TASK_ID,
        request_id=REQUEST_ID,
        artifact_ref=ARTIFACT,
        policy={"pages": [1, 2], MODE: STRICT},
    )
    second = SubmitRequest(
        task_id=TASK_ID,
        request_id=REQUEST_ID,
        artifact_ref=ARTIFACT,
        policy={MODE: STRICT, "pages": [1, 2]},
    )

    assert request_fingerprint(first) == request_fingerprint(second)
    assert first.effective_retention_seconds == DEFAULT_RETENTION_SECONDS


def test_submission_rejects_url_or_path_reference() -> None:
    with pytest.raises(ValueError, match="opaque capability"):
        SubmitRequest(
            task_id=TASK_ID,
            request_id=REQUEST_ID,
            artifact_ref="https://storage.example/object",
        )


def test_artifact_policy_changes_fingerprint() -> None:
    request = SubmitRequest(
        task_id=TASK_ID,
        request_id=REQUEST_ID,
        artifact_ref=ARTIFACT,
        policy={MODE: STRICT},
    )
    changed = SubmitRequest(
        task_id=TASK_ID,
        request_id=REQUEST_ID,
        artifact_ref="v1.two",
        policy={MODE: STRICT},
    )

    assert request_fingerprint(request) != request_fingerprint(changed)


def test_task_event_contains_stable_keys() -> None:
    request = SubmitRequest(
        task_id=TASK_ID,
        request_id=REQUEST_ID,
        artifact_ref=ARTIFACT,
        policy={MODE: STRICT},
    )
    submitted_at = EVENT_TIME
    expires_at = EVENT_EXPIRY

    event = task_event_payload(
        request,
        event_id="event-1",
        submitted_at=submitted_at,
        retention_expires_at=expires_at,
    )

    assert event["event_type"] == "sird.task.submitted.v1"
    assert event["event_id"] == "event-1"
    assert event["task_id"] == "task-1"
    assert event["request_id"] == "request-1"
    assert event["retention_expires_at"] == expires_at.isoformat()


def test_workflow_requires_explicit_allow_list() -> None:
    with pytest.raises(ValueError, match="authorized_callers"):
        WorkflowConfig(
            database_url="postgresql+psycopg://user:pass@localhost/db",
            rabbitmq_url="amqps://localhost:5671/sird",
        )


def test_rabbitmq_client_requires_tls() -> None:
    config = RabbitMQProducerConfig("amqps://localhost:5671/sird")
    assert config.amqp_url.startswith("amqps://")


def test_rabbitmq_client_rejects_plaintext() -> None:
    with pytest.raises(ValueError, match="TLS"):
        RabbitMQProducerConfig("amqp://localhost:5672/sird")
