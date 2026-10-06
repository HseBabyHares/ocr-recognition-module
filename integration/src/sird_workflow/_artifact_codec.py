"""Canonical encoding and decoding for signed artifact envelopes."""

import base64
import binascii
import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sird_workflow._artifact_capability_errors import MalformedCapabilityError
from sird_workflow._artifact_validation import normalise_expiry


def expiry_claim(candidate: datetime) -> str:
    return normalise_expiry(candidate).isoformat().replace("+00:00", "Z")


def parse_expiry(candidate: object) -> datetime:
    if not isinstance(candidate, str):
        raise MalformedCapabilityError("capability expiry is malformed")
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MalformedCapabilityError(
            "capability expiry is malformed"
        ) from exc
    try:
        return normalise_expiry(parsed)
    except ValueError as exc:
        raise MalformedCapabilityError(
            "capability expiry is malformed"
        ) from exc


def canonical_json(claims: Mapping[str, Any]) -> bytes:
    try:
        encoded = json.dumps(
            claims,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise MalformedCapabilityError(
            "capability claims are not canonicalizable"
        ) from exc
    return encoded.encode("utf-8")


def b64_encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def b64_decode(encoded_value: object) -> bytes:
    if (
        not isinstance(encoded_value, str)
        or not encoded_value
        or any(
            character
            not in (
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
            )
            for character in encoded_value
        )
    ):
        raise MalformedCapabilityError(
            "capability envelope encoding is malformed"
        )
    try:
        return base64.urlsafe_b64decode(
            encoded_value + "=" * (-len(encoded_value) % 4)
        )
    except (binascii.Error, ValueError) as exc:
        raise MalformedCapabilityError(
            "capability envelope encoding is malformed"
        ) from exc
