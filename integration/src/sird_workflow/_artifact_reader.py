"""Bounded artifact source and decoder access."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Collection
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from sird_workflow._artifact_capability_errors import (
    ArtifactSecurityError,
    CapabilityExpiredError,
)
from sird_workflow._artifact_models import ArtifactCapability, ArtifactRef
from sird_workflow._artifact_read_errors import (
    ArtifactChecksumError,
    ArtifactDecodeError,
    ArtifactPolicyError,
    ArtifactReadError,
    ArtifactSizeMismatchError,
)
from sird_workflow._artifact_signing import ArtifactCapabilityValidator
from sird_workflow._artifact_validation import (
    normalise_expiry,
    normalise_media_type,
)


class ArtifactSource(Protocol):
    """Source boundary that returns bytes for one already-owned object
    reference."""

    def read(self, artifact: ArtifactRef) -> bytes:
        """Read object bytes without exposing a URL or path to callers."""


class ArtifactDecoder(Protocol):
    """Decoder boundary. It is called only after all artifact guards pass."""

    def __call__(self, input_bytes: bytes) -> Any:
        """Decode bounded, validated bytes."""


@dataclass(frozen=True, slots=True)
class ArtifactReadPolicy:
    """Limits enforced before bytes are passed to a decoder."""

    max_bytes: int
    allowed_media_types: Collection[str]

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_bytes, bool)
            or not isinstance(self.max_bytes, int)
            or self.max_bytes <= 0
        ):
            raise ValueError("max_bytes must be a positive integer")
        media_types = frozenset(
            normalise_media_type(media_type)
            for media_type in self.allowed_media_types
        )
        if not media_types:
            raise ValueError("allowed_media_types must not be empty")
        object.__setattr__(self, "allowed_media_types", media_types)

    def enforce(self, capability: ArtifactCapability) -> None:
        if capability.size > self.max_bytes:
            raise ArtifactPolicyError(
                "artifact exceeds the decoder byte limit"
            )
        if capability.media_type not in self.allowed_media_types:
            raise ArtifactPolicyError("artifact media type is not allowed")


class ArtifactReader[DecodedT]:
    """Validate and bound one artifact before invoking a decoder."""

    def __init__(
        self,
        source: ArtifactSource,
        validator: ArtifactCapabilityValidator,
        policy: ArtifactReadPolicy,
    ) -> None:
        self._source = source
        self._validator = validator
        self._policy = policy

    def read(self, token: str, **options: Any) -> bytes:
        """Return bytes only after claims and task retention checks pass."""
        _reject_unknown_options(options)
        capability = self._validator.validate(token, **options)
        now = options.get("now")
        retention_expires_at = options.get("retention_expires_at")
        artifact = options["artifact"]
        if retention_expires_at is not None:
            current_time = (
                datetime.now(UTC) if now is None else normalise_expiry(now)
            )
            if normalise_expiry(retention_expires_at) <= current_time:
                raise CapabilityExpiredError(
                    "task result retention has expired"
                )
        self._policy.enforce(capability)
        return _read_bytes(self._source, artifact, capability, self._policy)

    def decode(
        self, decoder: ArtifactDecoder, token: str, **options: Any
    ) -> DecodedT:
        """Invoke the decoder only with validated, bounded bytes."""

        artifact_bytes = self.read(token, **options)
        try:
            return decoder(artifact_bytes)  # type: ignore[return-value]
        except ArtifactSecurityError:
            raise
        except Exception as exc:
            raise ArtifactDecodeError("artifact decoder failed") from exc


def _read_bytes(
    source: ArtifactSource,
    artifact: ArtifactRef,
    capability: ArtifactCapability,
    policy: ArtifactReadPolicy,
) -> bytes:
    try:
        artifact_bytes = source.read(artifact)
    except Exception as exc:
        raise ArtifactReadError("artifact source read failed") from exc
    if not isinstance(artifact_bytes, (bytes, bytearray, memoryview)):
        raise ArtifactReadError(
            "artifact source returned an invalid byte sequence"
        )
    _validate_bytes(artifact_bytes, capability, policy)
    return (
        artifact_bytes
        if isinstance(artifact_bytes, bytes)
        else bytes(artifact_bytes)
    )


def _validate_bytes(
    artifact_bytes: bytes | bytearray | memoryview,
    capability: ArtifactCapability,
    policy: ArtifactReadPolicy,
) -> None:
    if (
        len(artifact_bytes) > policy.max_bytes
        or len(artifact_bytes) != capability.size
    ):
        raise ArtifactSizeMismatchError(
            "artifact byte count does not match signed claims"
        )
    digest = hashlib.sha256(artifact_bytes).hexdigest()
    if not hmac.compare_digest(digest, capability.checksum):
        raise ArtifactChecksumError(
            "artifact checksum does not match signed claims"
        )


def _reject_unknown_options(options: dict[str, Any]) -> None:
    allowed = {
        "artifact",
        "task_id",
        "request_id",
        "audience",
        "now",
        "retention_expires_at",
    }
    unexpected = set(options) - allowed
    if unexpected:
        name = next(iter(unexpected))
        raise TypeError(f"unexpected keyword argument: {name}")
