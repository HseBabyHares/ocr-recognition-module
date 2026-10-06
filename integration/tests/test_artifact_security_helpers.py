from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from hashlib import sha256

from sird_workflow.artifact_security import (
    ArtifactCapability,
    ArtifactCapabilitySigner,
    ArtifactCapabilityValidator,
    ArtifactRef,
)

CURRENT_TIME = datetime.fromisoformat("2030-01-01T00:00:00+00:00")
ISSUER = "sird"
AUDIENCE = "ocr-worker"
PDF_MEDIA_TYPE = "application/pdf"
TASK_ID = "task-1"
REQUEST_ID = "request-1"
ARTIFACT_DATA = b"bounded artifact input"
CHECKSUM = sha256(ARTIFACT_DATA).hexdigest()
REF = ArtifactRef(
    object_id="opaque-object-7",
    generation="generation-3",
    checksum=CHECKSUM,
    media_type=PDF_MEDIA_TYPE,
    size=len(ARTIFACT_DATA),
)


class Source:
    def __init__(self, artifact_bytes: bytes) -> None:
        self._artifact_bytes = artifact_bytes
        self.reads = 0

    def read(self, artifact: ArtifactRef) -> bytes:
        self.reads += 1
        return self._artifact_bytes


def record_data(seen: list[bytes], input_bytes: bytes) -> int:
    seen.append(input_bytes)
    return len(input_bytes)


def record_data_only(seen: list[bytes], input_bytes: bytes) -> None:
    seen.append(input_bytes)


def signer(issuer: str = ISSUER) -> ArtifactCapabilitySigner:
    return ArtifactCapabilitySigner(
        key_id="local-v1", key=b"test-only-secret", issuer=issuer
    )


def capability(**changes: object) -> ArtifactCapability:
    capability_fields: dict[str, object] = {
        "task_id": TASK_ID,
        "request_id": REQUEST_ID,
        "audience": AUDIENCE,
        "artifact": REF,
        "issuer": ISSUER,
        "expires_at": CURRENT_TIME + timedelta(minutes=5),
    }
    capability_fields.update(changes)
    artifact = capability_fields.pop("artifact")
    assert isinstance(artifact, ArtifactRef)
    return ArtifactCapability.from_artifact(
        artifact=artifact, **capability_fields
    )


def validator() -> ArtifactCapabilityValidator:
    return ArtifactCapabilityValidator(
        {"local-v1": b"test-only-secret"},
        issuer=ISSUER,
        audience=AUDIENCE,
    )


def changed_artifact(
    change: str, artifact_changes: Mapping[str, str | int]
) -> ArtifactRef:
    if change not in artifact_changes:
        return REF
    artifact_fields = {
        "object_id": REF.object_id,
        "generation": REF.generation,
        "checksum": REF.checksum,
        "media_type": REF.media_type,
        "size": REF.size,
    }
    artifact_fields[change] = artifact_changes[change]
    return ArtifactRef(**artifact_fields)
