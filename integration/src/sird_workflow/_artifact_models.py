"""Immutable artifact references and signed capability claims."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from sird_workflow._artifact_capability_errors import MalformedCapabilityError
from sird_workflow._artifact_codec import expiry_claim, parse_expiry
from sird_workflow._artifact_validation import (
    normalise_checksum,
    normalise_expiry,
    normalise_generation,
    normalise_media_type,
    normalise_object_id,
    require_text,
)

_CLAIM_TASK = "task_id"
_CLAIM_REQUEST = "request_id"
_CLAIM_AUDIENCE = "audience"
_CLAIM_OBJECT = "object_id"
_CLAIM_GENERATION = "generation"
_CLAIM_CHECKSUM = "checksum"
_CLAIM_MEDIA = "media_type"
_CLAIM_SIZE = "size"
_CLAIM_ISSUER = "issuer"
_CLAIM_EXPIRY = "expires_at"

_REQUIRED_CLAIMS = frozenset(
    (
        _CLAIM_TASK,
        _CLAIM_REQUEST,
        _CLAIM_AUDIENCE,
        _CLAIM_OBJECT,
        _CLAIM_GENERATION,
        _CLAIM_CHECKSUM,
        _CLAIM_MEDIA,
        _CLAIM_SIZE,
        _CLAIM_ISSUER,
        _CLAIM_EXPIRY,
    )
)


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    """SIRD-owned opaque object identity and immutable object metadata."""

    object_id: str
    generation: str | int
    checksum: str
    media_type: str
    size: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "object_id", normalise_object_id(self.object_id)
        )
        object.__setattr__(
            self, "generation", normalise_generation(self.generation)
        )
        object.__setattr__(self, "checksum", normalise_checksum(self.checksum))
        object.__setattr__(
            self, "media_type", normalise_media_type(self.media_type)
        )
        if (
            isinstance(self.size, bool)
            or not isinstance(self.size, int)
            or self.size < 0
        ):
            raise ValueError("size must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class ArtifactCapability:
    """Claims signed for one task, request, audience, and artifact version."""

    task_id: str
    request_id: str
    audience: str
    object_id: str
    generation: str | int
    checksum: str
    media_type: str
    size: int
    issuer: str
    expires_at: datetime

    def __post_init__(self) -> None:
        for name in ("task_id", "request_id", "audience", "issuer"):
            object.__setattr__(
                self, name, require_text(getattr(self, name), name)
            )
        object.__setattr__(
            self, "object_id", normalise_object_id(self.object_id)
        )
        object.__setattr__(
            self, "generation", normalise_generation(self.generation)
        )
        object.__setattr__(self, "checksum", normalise_checksum(self.checksum))
        object.__setattr__(
            self, "media_type", normalise_media_type(self.media_type)
        )
        if (
            isinstance(self.size, bool)
            or not isinstance(self.size, int)
            or self.size < 0
        ):
            raise ValueError("size must be a non-negative integer")
        object.__setattr__(
            self, "expires_at", normalise_expiry(self.expires_at)
        )

    @classmethod
    def from_artifact(cls, **claims: Any) -> ArtifactCapability:
        """Build claims from one immutable artifact reference."""

        artifact: ArtifactRef = claims.pop("artifact")
        return cls(
            object_id=artifact.object_id,
            generation=artifact.generation,
            checksum=artifact.checksum,
            media_type=artifact.media_type,
            size=artifact.size,
            **claims,
        )

    def claims(self) -> dict[str, Any]:
        """Return the canonicalizable claims map, excluding envelope fields."""

        return {
            _CLAIM_AUDIENCE: self.audience,
            _CLAIM_CHECKSUM: self.checksum,
            _CLAIM_EXPIRY: expiry_claim(self.expires_at),
            _CLAIM_GENERATION: self.generation,
            _CLAIM_ISSUER: self.issuer,
            _CLAIM_MEDIA: self.media_type,
            _CLAIM_OBJECT: self.object_id,
            _CLAIM_REQUEST: self.request_id,
            _CLAIM_SIZE: self.size,
            _CLAIM_TASK: self.task_id,
        }

    @classmethod
    def from_claims(cls, claims: object) -> ArtifactCapability:
        if not isinstance(claims, dict):
            raise MalformedCapabilityError("capability claims are malformed")
        if set(claims) != _REQUIRED_CLAIMS:
            raise MalformedCapabilityError("capability claims are incomplete")
        claims = cast(dict[str, Any], claims)
        try:
            return cls(**_parse_claims(claims))
        except (KeyError, TypeError, ValueError) as exc:
            raise MalformedCapabilityError(
                "capability claims are malformed"
            ) from exc


def _parse_claims(claims: dict[str, Any]) -> dict[str, Any]:
    parsed_claims = dict(claims)
    parsed_claims[_CLAIM_EXPIRY] = parse_expiry(parsed_claims[_CLAIM_EXPIRY])
    return parsed_claims
