"""Verify the HMAC artifact capability that the Process service issues.

Token: ``v1.<b64url canonical JSON envelope>.<b64url HMAC-SHA256>``.
The envelope is ``{"claims": {...}, "kid": ..., "v": 1}``.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sird_recognition._capability_token import (
    checked_claims,
    denied,
    expiry,
    signed_envelope,
)
from sird_recognition._runtime_request import RecognitionError
from sird_recognition.codes import TechnicalCode

_MIN_KEY_BYTES = 32


@dataclass(frozen=True, slots=True)
class CapabilityClaims:
    """Signed claims that bind one object version to one task."""

    object_id: str
    object_key: str
    generation: str
    checksum: str
    media_type: str
    size: int


@dataclass(frozen=True, slots=True)
class CapabilityVerifier:
    """Fail-closed verifier for one issuer and one audience."""

    keys: Mapping[str, bytes]
    issuer: str
    audience: str
    clock: Callable[[], datetime] = field(default=lambda: datetime.now(UTC))

    def verify(
        self, token: str, *, task_id: str | None, request_id: str
    ) -> CapabilityClaims:
        """Return the claims or raise a typed ``RecognitionError``."""
        claims = self._authentic_claims(token)
        if (
            claims["issuer"] != self.issuer
            or claims["audience"] != self.audience
            or expiry(claims["expires_at"]) <= self.clock()
        ):
            raise denied()
        if claims["request_id"] != request_id or (
            task_id is not None and claims["task_id"] != task_id
        ):
            raise RecognitionError(TechnicalCode.CAPABILITY_MISMATCH)
        return CapabilityClaims(
            object_id=claims["object_id"],
            object_key=claims["object_key"],
            generation=claims["generation"],
            checksum=claims["checksum"],
            media_type=claims["media_type"],
            size=claims["size"],
        )

    def _authentic_claims(self, token: str) -> dict[str, Any]:
        payload, mac, envelope = signed_envelope(token)
        kid = envelope["kid"]
        key = self.keys.get(kid) if isinstance(kid, str) else None
        if key is None or envelope["v"] != 1:
            raise denied()
        if not hmac.compare_digest(_mac(key, payload), mac):
            raise denied()
        return checked_claims(envelope["claims"])


def parse_keys(configured: str) -> dict[str, bytes]:
    """Parse ``kid:hex[,kid:hex]``; every key must have 32 bytes or more."""
    return dict(_key_entry(entry) for entry in configured.split(","))


def _key_entry(entry: str) -> tuple[str, bytes]:
    kid, separator, hex_key = entry.strip().partition(":")
    secret = bytes.fromhex(hex_key)
    if not separator or not kid or len(secret) < _MIN_KEY_BYTES:
        raise ValueError("capability keys must use kid:hex of 32+ bytes")
    return kid, secret


def _mac(key: bytes, payload: bytes) -> bytes:
    return hmac.new(key, payload, hashlib.sha256).digest()
