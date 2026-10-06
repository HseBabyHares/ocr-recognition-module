"""Capability signing and request validation services."""

import hashlib
import hmac
from collections.abc import Mapping
from datetime import datetime
from typing import TypedDict, cast

from sird_workflow._artifact_binding import (
    ValidationContext,
    validate_capability,
)
from sird_workflow._artifact_capability_errors import (
    CapabilityClaimMismatchError,
)
from sird_workflow._artifact_codec import b64_encode, canonical_json
from sird_workflow._artifact_constants import PROTOCOL_VERSION
from sird_workflow._artifact_models import ArtifactCapability, ArtifactRef
from sird_workflow._artifact_token import verify_token
from sird_workflow._artifact_validation import require_text


class _ValidationOptions(TypedDict, total=False):
    task_id: str
    request_id: str
    artifact: ArtifactRef
    audience: str
    now: datetime | None
    retention_expires_at: datetime


_AUDIENCE_OPTION = "audience"
_VALIDATION_OPTION_NAMES = frozenset(
    (
        "task_id",
        "request_id",
        "artifact",
        _AUDIENCE_OPTION,
        "now",
        "retention_expires_at",
    ),
)


def _typed_validation_options(
    options: Mapping[str, object],
) -> _ValidationOptions:
    unexpected = set(options) - _VALIDATION_OPTION_NAMES
    if unexpected:
        raise TypeError(
            f"unexpected keyword argument: {next(iter(unexpected))}"
        )
    return cast(_ValidationOptions, options)


class ArtifactCapabilitySigner:
    """Issue and verify versioned HMAC-SHA256 capability envelopes.

    Key storage and identity selection are production concerns outside this
    local primitive. The signer receives an already selected key explicitly.
    """

    def __init__(
        self,
        *,
        key_id: str,
        key: bytes,
        issuer: str,
        version: int = PROTOCOL_VERSION,
    ) -> None:
        self._key_id = require_text(key_id, "key_id")
        if not isinstance(key, bytes) or not key:
            raise ValueError("key must be non-empty bytes")
        self._key = key
        self._issuer = require_text(issuer, "issuer")
        if version != PROTOCOL_VERSION:
            raise ValueError("unsupported capability protocol version")
        self._version = version

    @property
    def key_id(self) -> str:
        return self._key_id

    @property
    def issuer(self) -> str:
        return self._issuer

    @property
    def version(self) -> int:
        return self._version

    def sign(self, capability: ArtifactCapability) -> str:
        if not isinstance(capability, ArtifactCapability):
            raise TypeError("capability must be an ArtifactCapability")
        if capability.issuer != self._issuer:
            raise CapabilityClaimMismatchError(
                "capability issuer does not match signer"
            )
        envelope = {
            "claims": capability.claims(),
            "kid": self._key_id,
            "v": self._version,
        }
        payload = canonical_json(envelope)
        mac = hmac.new(self._key, payload, hashlib.sha256).digest()
        return f"v{self._version}.{b64_encode(payload)}.{b64_encode(mac)}"

    def verify(self, token: str) -> ArtifactCapability:
        return verify_token(token, {self._key_id: self._key}, self._version)


class ArtifactCapabilityValidator:
    """Verify a capability and enforce its request, audience, and artifact
    claims."""

    def __init__(
        self,
        keys: Mapping[str, bytes] | ArtifactCapabilitySigner,
        *,
        issuer: str,
        audience: str,
        version: int = PROTOCOL_VERSION,
    ) -> None:
        self._keys = _key_map(keys)
        self._issuer = require_text(issuer, "issuer")
        self._audience = require_text(audience, _AUDIENCE_OPTION)
        if version != PROTOCOL_VERSION:
            raise ValueError("unsupported capability protocol version")
        self._version = version

    def verify(self, token: str) -> ArtifactCapability:
        """Verify only the envelope MAC and claim shape."""

        return verify_token(token, self._keys, self._version)

    def validate(self, token: str, **options: object) -> ArtifactCapability:
        """Verify and bind one token to the expected task and artifact."""
        typed_options = _typed_validation_options(options)
        capability = self.verify(token)
        expected_audience = _expected_audience(options, self._audience)
        context = ValidationContext(
            task_id=typed_options["task_id"],
            request_id=typed_options["request_id"],
            artifact=typed_options["artifact"],
            audience=expected_audience,
            issuer=self._issuer,
            now=typed_options.get("now"),
        )
        return validate_capability(capability, context)


def _expected_audience(options: Mapping[str, object], default: str) -> str:
    audience = options.get(_AUDIENCE_OPTION)
    return (
        default
        if audience is None
        else require_text(audience, _AUDIENCE_OPTION)
    )


def _key_map(
    keys: Mapping[str, bytes] | ArtifactCapabilitySigner,
) -> dict[str, bytes]:
    if isinstance(keys, ArtifactCapabilitySigner):
        return {keys.key_id: keys._key}
    if not isinstance(keys, Mapping) or not keys:
        raise ValueError("keys must be a non-empty key mapping")
    entries: dict[str, bytes] = {}
    for key_id, key in keys.items():
        normalised_id = require_text(key_id, "key_id")
        if not isinstance(key, bytes) or not key:
            raise ValueError("capability keys must be non-empty bytes")
        entries[normalised_id] = key
    return entries
