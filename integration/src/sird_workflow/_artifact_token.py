"""Fail-closed parsing and authentication of capability envelopes."""

import hashlib
import hmac
import json
from collections.abc import Mapping
from typing import Any, cast

from sird_workflow._artifact_capability_errors import (
    CapabilitySignatureError,
    MalformedCapabilityError,
)
from sird_workflow._artifact_codec import b64_decode, canonical_json
from sird_workflow._artifact_constants import MAX_TOKEN_BYTES
from sird_workflow._artifact_models import ArtifactCapability

_MALFORMED_ENVELOPE = "capability envelope is malformed"


def verify_token(
    token: str, keys: Mapping[str, bytes], version: int
) -> ArtifactCapability:
    parts = _token_parts(token, version)
    payload = b64_decode(parts[1])
    supplied_mac = b64_decode(parts[2])
    envelope = _decode_envelope(payload)
    key = _key_for_envelope(envelope, keys, version)
    _verify_mac(key, payload, supplied_mac)
    return ArtifactCapability.from_claims(envelope["claims"])


def _token_parts(token: object, version: int) -> list[str]:
    if not isinstance(token, str) or len(token) > MAX_TOKEN_BYTES:
        raise MalformedCapabilityError("capability token is malformed")
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != f"v{version}":
        raise MalformedCapabilityError(_MALFORMED_ENVELOPE)
    return parts


def _decode_envelope(payload: bytes) -> dict[str, Any]:
    try:
        envelope = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MalformedCapabilityError(_MALFORMED_ENVELOPE) from exc
    if not isinstance(envelope, dict) or set(envelope) != {
        "claims",
        "kid",
        "v",
    }:
        raise MalformedCapabilityError(_MALFORMED_ENVELOPE)
    return cast(dict[str, Any], envelope)


def _key_for_envelope(
    envelope: Mapping[str, Any], keys: Mapping[str, bytes], version: int
) -> bytes:
    if envelope["v"] != version or not isinstance(envelope["kid"], str):
        raise MalformedCapabilityError(_MALFORMED_ENVELOPE)
    key = keys.get(envelope["kid"])
    if key is None:
        raise CapabilitySignatureError("capability key is unavailable")
    return key


def _verify_mac(key: bytes, payload: bytes, supplied_mac: bytes) -> None:
    expected_mac = hmac.new(
        key, canonical_json(json.loads(payload)), hashlib.sha256
    ).digest()
    if not hmac.compare_digest(expected_mac, supplied_mac):
        raise CapabilitySignatureError("capability signature is invalid")
