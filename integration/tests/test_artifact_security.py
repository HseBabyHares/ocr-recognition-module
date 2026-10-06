from __future__ import annotations

from hashlib import sha256

import pytest
import test_artifact_security_helpers as helpers
from sird_workflow import artifact_security


def test_capability_sign_verify_round_trip() -> None:
    token = helpers.signer().sign(helpers.capability())

    assert token.startswith("v1.")
    verified = helpers.signer().verify(token)
    validated = helpers.validator().validate(
        token,
        task_id=helpers.TASK_ID,
        request_id=helpers.REQUEST_ID,
        artifact=helpers.REF,
        now=helpers.CURRENT_TIME,
    )

    assert verified == validated == helpers.capability()
    assert "opaque-object-7" not in token
    assert helpers.PDF_MEDIA_TYPE not in token


def test_tampered_capability_rejected() -> None:
    token = helpers.signer().sign(helpers.capability())
    tampered = token[:-1] + _alternate_suffix(token)

    with pytest.raises(artifact_security.CapabilitySignatureError):
        helpers.validator().verify(tampered)


def _alternate_suffix(token: str) -> str:
    if token[-1] == "A":
        return "B"
    return "A"


def test_malformed_capability_is_rejected() -> None:
    with pytest.raises(artifact_security.MalformedCapabilityError):
        helpers.validator().verify("not-a-capability")


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ("task_id", artifact_security.CapabilityClaimMismatchError),
        ("request_id", artifact_security.CapabilityClaimMismatchError),
        ("audience", artifact_security.CapabilityClaimMismatchError),
        ("issuer", artifact_security.CapabilityClaimMismatchError),
        ("generation", artifact_security.CapabilityClaimMismatchError),
        ("checksum", artifact_security.CapabilityClaimMismatchError),
        ("media_type", artifact_security.CapabilityClaimMismatchError),
        ("size", artifact_security.CapabilityClaimMismatchError),
    ],
)
def test_validator_rejects_binding_mismatch(
    change: str, expected: type[Exception]
) -> None:
    changed_values = {
        "task_id": "task-2",
        "request_id": "request-2",
        "audience": "other-worker",
        "issuer": "other-issuer",
    }
    artifact_changes = {
        "generation": "generation-4",
        "checksum": sha256(b"different").hexdigest(),
        "media_type": "text/plain",
        "size": helpers.REF.size + 1,
    }
    changed_ref = helpers.changed_artifact(change, artifact_changes)
    changed_signer = (
        helpers.signer("other-issuer")
        if change == "issuer"
        else helpers.signer()
    )
    token = changed_signer.sign(
        helpers.capability(
            artifact=changed_ref, **_claim_change(change, changed_values)
        )
    )

    with pytest.raises(expected):
        helpers.validator().validate(
            token,
            task_id=helpers.TASK_ID,
            request_id=helpers.REQUEST_ID,
            artifact=helpers.REF,
            now=helpers.CURRENT_TIME,
        )


def _claim_change(change: str, claim_values: dict[str, str]) -> dict[str, str]:
    return {change: claim_values[change]} if change in claim_values else {}


def test_validator_rejects_expired_capability() -> None:
    token = helpers.signer().sign(
        helpers.capability(expires_at=helpers.CURRENT_TIME)
    )

    with pytest.raises(artifact_security.CapabilityExpiredError):
        helpers.validator().validate(
            token,
            task_id=helpers.TASK_ID,
            request_id=helpers.REQUEST_ID,
            artifact=helpers.REF,
            now=helpers.CURRENT_TIME,
        )
