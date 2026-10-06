"""Request and artifact binding checks for verified capabilities."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sird_workflow._artifact_capability_errors import (
    CapabilityClaimMismatchError,
    CapabilityExpiredError,
)
from sird_workflow._artifact_models import ArtifactCapability, ArtifactRef
from sird_workflow._artifact_validation import normalise_expiry, require_text


@dataclass(frozen=True, slots=True)
class ValidationContext:
    task_id: str
    request_id: str
    artifact: ArtifactRef
    audience: str
    issuer: str
    now: datetime | None


def validate_capability(
    capability: ArtifactCapability, context: ValidationContext
) -> ArtifactCapability:
    _check_issuer_audience(capability, context)
    _check_request_bindings(capability, context)
    current_time = (
        datetime.now(UTC)
        if context.now is None
        else normalise_expiry(context.now)
    )
    if capability.expires_at <= current_time:
        raise CapabilityExpiredError("artifact capability has expired")
    expected_claims = ArtifactCapability.from_artifact(
        task_id=context.task_id,
        request_id=context.request_id,
        audience=context.audience,
        artifact=context.artifact,
        issuer=context.issuer,
        expires_at=capability.expires_at,
    )
    _check_artifact_claims(capability, expected_claims)
    return capability


def _check_issuer_audience(
    capability: ArtifactCapability, context: ValidationContext
) -> None:
    if capability.issuer != context.issuer:
        raise CapabilityClaimMismatchError(
            "capability issuer does not match validator"
        )
    if capability.audience != context.audience:
        raise CapabilityClaimMismatchError(
            "capability audience does not match request"
        )


def _check_request_bindings(
    capability: ArtifactCapability, context: ValidationContext
) -> None:
    if capability.task_id != require_text(context.task_id, "task_id"):
        raise CapabilityClaimMismatchError(
            "capability task binding does not match request"
        )
    if capability.request_id != require_text(context.request_id, "request_id"):
        raise CapabilityClaimMismatchError(
            "capability request binding does not match request"
        )


def _check_artifact_claims(
    capability: ArtifactCapability,
    expected_claims: ArtifactCapability,
) -> None:
    actual_claims = (
        capability.object_id,
        capability.generation,
        capability.checksum,
        capability.media_type,
        capability.size,
    )
    expected_values = (
        expected_claims.object_id,
        expected_claims.generation,
        expected_claims.checksum,
        expected_claims.media_type,
        expected_claims.size,
    )
    if actual_claims != expected_values:
        raise CapabilityClaimMismatchError(
            "capability artifact claims do not match request"
        )
