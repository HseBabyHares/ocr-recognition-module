"""Synthetic Process capability tokens for the OCR server tests."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime

from sird_recognition.artifact_capability import (
    CapabilityVerifier,
    parse_keys,
)
from tests import _grpc_fixtures as grpc_fixtures

KEY_HEX = "abababababababababababababababababababababababababababababababab"
NOW = datetime.fromisoformat("2026-10-13T12:00:00+00:00")
IMAGE = b"synthetic-image-bytes"
CHECKSUM = hashlib.sha256(IMAGE).hexdigest()
OBJECT_ID = "src-1"
OBJECT_KEY = "task-service/sources/1/0"
VERIFIER = CapabilityVerifier(
    keys=parse_keys(f"v1-k1:{KEY_HEX}"),
    issuer="process-service",
    audience="ocr.service",
    clock=lambda: NOW,
)


def issue(**overrides: object) -> str:
    """Build a token exactly like Process LocalArtifactCapabilityIssuer."""
    claims = {
        "audience": "ocr.service",
        "checksum": CHECKSUM,
        "expires_at": "2026-10-13T12:05:00Z",
        "generation": "opaque-generation",
        "issuer": "process-service",
        "media_type": "image/jpeg",
        "object_id": OBJECT_ID,
        "object_key": OBJECT_KEY,
        "request_id": grpc_fixtures.REQUEST_ID,
        "size": len(IMAGE),
        "task_id": grpc_fixtures.TASK_ID,
        **overrides,
    }
    payload = json.dumps(
        {"claims": claims, "kid": "v1-k1", "v": 1},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    mac = hmac.new(bytes.fromhex(KEY_HEX), payload, hashlib.sha256).digest()
    return ".".join(("v1", _b64(payload), _b64(mac)))


def tampered() -> str:
    """Return a valid token whose MAC is all zero bytes."""
    version, payload, _ = issue().split(".")
    return ".".join(
        (version, payload, _b64(bytes(len(hashlib.sha256().digest()))))
    )


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
