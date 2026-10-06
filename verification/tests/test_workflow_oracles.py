from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from types import SimpleNamespace

from sird_workflow.artifact_security import (
    ArtifactCapability,
    ArtifactCapabilitySigner,
    ArtifactCapabilityValidator,
    ArtifactRef,
)
from sird_workflow.attempts import AttemptBudget
from sird_workflow.dead_letter import (
    BrokerAcknowledgement,
    DeadLetterEvent,
    DeadLetterOutbox,
)

from sird_verification.adapters import (
    ArtifactCapabilityAdapter,
    AttemptBudgetAdapter,
    DeadLetterAdapter,
)
from sird_verification.contracts import OracleStatus
from sird_verification.oracles import (
    artifact_capability_rejection_oracle,
    outbox_dlt_ack_gating_oracle,
    shared_attempt_budget_oracle,
)

YEAR = 2030
MONTH = 1
DAY = 1
EXPIRY_MINUTES = 5
ONE = 1
NOW = datetime(YEAR, MONTH, DAY, tzinfo=UTC)
KEY_ID = "local-v1"
KEY = b"test-only-key"
TASK_ID = "task-1"
REQUEST_ID = "request-1"
AUDIENCE = "ocr-worker"
ISSUER = "sird"
EVENT_ID = "event-1"
BROKER_MESSAGE_ID = "broker-1"
ARTIFACT = ArtifactRef(
    object_id="opaque-object",
    generation="generation-1",
    checksum=sha256(b"bounded data").hexdigest(),
    media_type="application/pdf",
    size=len(b"bounded data"),
)


def _capability_adapter() -> tuple[ArtifactCapabilityAdapter, str]:
    capability = ArtifactCapability.from_artifact(
        task_id=TASK_ID,
        request_id=REQUEST_ID,
        audience=AUDIENCE,
        artifact=ARTIFACT,
        issuer=ISSUER,
        expires_at=NOW + timedelta(minutes=EXPIRY_MINUTES),
    )
    signer = ArtifactCapabilitySigner(
        key_id=KEY_ID,
        key=KEY,
        issuer=ISSUER,
    )
    validator = ArtifactCapabilityValidator(
        {KEY_ID: KEY},
        issuer=ISSUER,
        audience=AUDIENCE,
    )
    return ArtifactCapabilityAdapter(validator), signer.sign(capability)


class ConsumingBudget:
    attempts_used = 0

    def claim(
        self,
        worker_id: str,
        *,
        delivery_id: str,
    ) -> tuple[SimpleNamespace, SimpleNamespace]:
        attempts = self.attempts_used + ONE
        state = SimpleNamespace(attempts_used=attempts, claim=self.claim)
        lease = SimpleNamespace(
            worker_id=worker_id,
            delivery_id=delivery_id,
            fencing_token=attempts,
        )
        return state, lease


def _outbox() -> DeadLetterOutbox:
    return DeadLetterOutbox(
        event=DeadLetterEvent(
            event_id=EVENT_ID,
            task_id=TASK_ID,
            topic="sird.task.dead-letter.v1",
            payload={"reason": "bounded"},
            created_at=NOW,
        )
    )


class Publisher:
    def __init__(self, acknowledged: bool) -> None:
        self.acknowledged = acknowledged

    def publish(self, event: DeadLetterEvent) -> BrokerAcknowledgement:
        return BrokerAcknowledgement(
            event_id=event.event_id,
            acknowledged=self.acknowledged,
            broker_message_id=BROKER_MESSAGE_ID if self.acknowledged else None,
            acknowledged_at=NOW if self.acknowledged else None,
        )


class UnsafeOutbox:
    acknowledged = False

    def publish(self, _publisher: object) -> UnsafeOutbox:
        return self

    def commit_source_offset(self) -> SimpleNamespace:
        return SimpleNamespace(source_offset_committed=True)


class TestWorkflowOracles:
    def test_capability_rejection_reports_statuses(self) -> None:
        adapter, token = _capability_adapter()

        passed = artifact_capability_rejection_oracle(
            adapter,
            token,
            task_id="other-task",
            request_id=REQUEST_ID,
            artifact=ARTIFACT,
            now=NOW,
        )
        failed = artifact_capability_rejection_oracle(
            adapter,
            token,
            task_id=TASK_ID,
            request_id=REQUEST_ID,
            artifact=ARTIFACT,
            now=NOW,
        )
        blocked = artifact_capability_rejection_oracle(
            None,
            token,
            task_id=TASK_ID,
            request_id=REQUEST_ID,
            artifact=ARTIFACT,
            now=NOW,
        )

        assert passed.status is OracleStatus.PASS
        assert passed.observed == {"rejected": True}
        assert failed.status is OracleStatus.FAIL
        assert blocked.status is OracleStatus.BLOCKED
        assert token not in passed.reason

    def test_duplicate_delivery_uses_shared_attempt(self) -> None:
        passed = shared_attempt_budget_oracle(
            AttemptBudgetAdapter(AttemptBudget(task_id=TASK_ID))
        )
        failed = shared_attempt_budget_oracle(
            AttemptBudgetAdapter(ConsumingBudget())
        )
        blocked = shared_attempt_budget_oracle(None)

        assert passed.status is OracleStatus.PASS
        assert passed.observed["one_attempt_used"] is True
        assert passed.observed["fencing_advanced"] is True
        assert failed.status is OracleStatus.FAIL
        assert blocked.status is OracleStatus.BLOCKED

    def test_dead_letter_offset_requires_ack(self) -> None:
        negative_ack = outbox_dlt_ack_gating_oracle(
            DeadLetterAdapter(_outbox()),
            Publisher(False),
        )
        positive_ack = outbox_dlt_ack_gating_oracle(
            DeadLetterAdapter(_outbox()),
            Publisher(True),
        )
        failed = outbox_dlt_ack_gating_oracle(
            DeadLetterAdapter(UnsafeOutbox()),
            Publisher(False),
        )
        blocked = outbox_dlt_ack_gating_oracle(None, Publisher(False))

        assert (
            negative_ack.status,
            positive_ack.status,
            failed.status,
            blocked.status,
        ) == (
            OracleStatus.PASS,
            OracleStatus.PASS,
            OracleStatus.FAIL,
            OracleStatus.BLOCKED,
        )
        assert negative_ack.observed["offset_commit_blocked"] is True
        assert positive_ack.observed["offset_commit_allowed"] is True
