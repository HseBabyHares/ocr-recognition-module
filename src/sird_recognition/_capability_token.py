"""Decode the Process capability token without trusting its content.

The caller checks the HMAC; this module only parses and shape-checks.
"""

from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime
from typing import Any

from sird_recognition._runtime_request import RecognitionError
from sird_recognition.codes import TechnicalCode

_MAX_TOKEN_LENGTH = 131072
_TOKEN_PARTS = 3
_ENVELOPE_NAMES = frozenset(("claims", "kid", "v"))
_TEXT_CLAIMS = frozenset(
    (
        "audience",
        "checksum",
        "expires_at",
        "generation",
        "issuer",
        "media_type",
        "object_id",
        "object_key",
        "request_id",
        "task_id",
    )
)
_CLAIM_NAMES = frozenset((*_TEXT_CLAIMS, "size"))


def denied() -> RecognitionError:
    """Return the error for every untrusted or unauthorized token."""
    return RecognitionError(TechnicalCode.AUTHORIZATION_FAILED)


def signed_envelope(token: str) -> tuple[bytes, bytes, dict[str, Any]]:
    """Return the raw payload, the MAC and the decoded envelope."""
    payload, mac = _token_parts(token)
    try:
        envelope = _exact_object(json.loads(payload), _ENVELOPE_NAMES)
    except ValueError:
        raise denied() from None
    return payload, mac, envelope


def checked_claims(candidate: object) -> dict[str, Any]:
    """Return the claims when every claim has the expected type."""
    claims = _exact_object(candidate, _CLAIM_NAMES)
    size = claims["size"]
    texts_valid = all(
        isinstance(claims[name], str) and claims[name] for name in _TEXT_CLAIMS
    )
    if not texts_valid or isinstance(size, bool) or not isinstance(size, int):
        raise denied()
    if size <= 0:
        raise denied()
    return claims


def expiry(text: str) -> datetime:
    """Parse an ISO-8601 expiry that has a time zone."""
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise denied() from None
    if parsed.tzinfo is None:
        raise denied()
    return parsed


def _token_parts(token: str) -> tuple[bytes, bytes]:
    parts = token.split(".") if len(token) <= _MAX_TOKEN_LENGTH else []
    if len(parts) != _TOKEN_PARTS or parts[0] != "v1":
        raise denied()
    return _b64decode(parts[1]), _b64decode(parts[2])


def _b64decode(part: str) -> bytes:
    if not part or "=" in part:
        raise denied()
    try:
        return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))
    except (binascii.Error, ValueError):
        raise denied() from None


def _exact_object(candidate: Any, names: frozenset[str]) -> dict[str, Any]:
    if not isinstance(candidate, dict) or set(candidate) != names:
        raise denied()
    return candidate
