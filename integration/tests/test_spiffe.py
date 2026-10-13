from datetime import UTC, datetime, timedelta
from importlib import import_module

import pytest
from sird_workflow import spiffe

TRUSTED_ID = "spiffe://sird.example/backend/task"
CURRENT_YEAR = 2026
CURRENT_MONTH = 9
CURRENT_DAY = 20
CURRENT_HOUR = 12
RENEWAL_GRACE_SECONDS = 30
EXPIRY_MINUTES = 5
RENEWAL_OFFSET_SECONDS = 1
ISSUED_OFFSET_MINUTES = 1
NOW = datetime(
    CURRENT_YEAR, CURRENT_MONTH, CURRENT_DAY, CURRENT_HOUR, tzinfo=UTC
)


def test_authorizes_identity_and_role() -> None:
    identity = spiffe.SpiffeId.parse(TRUSTED_ID)
    policy = spiffe.SpiffeAuthorizationPolicy(
        allowed_roles={identity: spiffe.WorkloadRole.TASK_SERVICE},
    )
    credential = spiffe.WorkloadCredential(
        spiffe_id=identity,
        issued_at=NOW - timedelta(minutes=ISSUED_OFFSET_MINUTES),
        renewed_at=NOW - timedelta(seconds=RENEWAL_GRACE_SECONDS),
        expires_at=NOW + timedelta(minutes=EXPIRY_MINUTES),
    )

    assert spiffe.authorize_workload(
        policy, credential, spiffe.WorkloadRole.TASK_SERVICE, now=NOW
    )
    assert identity.as_text == TRUSTED_ID
    assert identity.trust_domain == "sird.example"
    assert identity.path == "/backend/task"


def test_rejects_unknown_and_malformed_identity() -> None:
    with pytest.raises(spiffe.MalformedSpiffeIdError):
        spiffe.SpiffeId.parse("https://sird.example/backend/task")
    with pytest.raises(spiffe.MalformedSpiffeIdError):
        spiffe.SpiffeId.parse("spiffe://sird.example")

    policy = spiffe.SpiffeAuthorizationPolicy(
        allowed_roles={TRUSTED_ID: spiffe.WorkloadRole.TASK_SERVICE},
    )
    credential = spiffe.WorkloadCredential(
        spiffe_id="spiffe://sird.example/backend/other",
        expires_at=NOW + timedelta(minutes=5),
    )
    with pytest.raises(spiffe.UnauthorizedWorkloadError):
        spiffe.authorize_workload(
            policy, credential, spiffe.WorkloadRole.TASK_SERVICE, now=NOW
        )


def test_rejects_wrong_role() -> None:
    policy = spiffe.SpiffeAuthorizationPolicy(
        allowed_roles={TRUSTED_ID: spiffe.WorkloadRole.TASK_SERVICE},
    )
    credential = spiffe.WorkloadCredential(
        spiffe_id=TRUSTED_ID,
        expires_at=NOW + timedelta(minutes=5),
    )

    with pytest.raises(spiffe.UnauthorizedWorkloadError):
        spiffe.authorize_workload(
            policy, credential, spiffe.WorkloadRole.OCR_SERVICE, now=NOW
        )


def test_rejects_expired_and_future_renewal() -> None:
    policy = spiffe.SpiffeAuthorizationPolicy(
        allowed_roles={TRUSTED_ID: spiffe.WorkloadRole.TASK_SERVICE},
    )
    expired = spiffe.WorkloadCredential(spiffe_id=TRUSTED_ID, expires_at=NOW)
    with pytest.raises(spiffe.ExpiredCredentialError):
        spiffe.validate_credential(expired, now=NOW)

    renewing = spiffe.WorkloadCredential(
        spiffe_id=TRUSTED_ID,
        renewed_at=NOW + timedelta(seconds=RENEWAL_OFFSET_SECONDS),
        expires_at=NOW + timedelta(minutes=EXPIRY_MINUTES),
    )
    with pytest.raises(ValueError, match="renewal"):
        spiffe.authorize_workload(
            policy, renewing, spiffe.WorkloadRole.TASK_SERVICE, now=NOW
        )


def test_empty_policy_fails_closed() -> None:
    with pytest.raises(spiffe.EmptyAuthorizationPolicyError):
        spiffe.SpiffeAuthorizationPolicy(allowed_roles={})


def test_root_api_does_not_export_spiffe() -> None:
    root_api = import_module("sird_workflow")
    for name in ("SpiffeId", "WorkloadRole", "authorize_workload"):
        with pytest.raises(AttributeError):
            getattr(root_api, name)
