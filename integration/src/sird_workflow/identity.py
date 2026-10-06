"""Pure helpers for idempotency and stable task-event mapping."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sird_workflow.models import SubmitRequest


def request_fingerprint(request: SubmitRequest) -> str:
    """Hash all request content that must remain stable for an identity."""

    fingerprint_input = {
        "artifact_ref": request.artifact_ref,
        "policy": request.policy,
        "retention_seconds": request.effective_retention_seconds,
    }
    encoded = json.dumps(
        fingerprint_input,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def task_event_payload(
    request: SubmitRequest,
    *,
    event_id: str,
    submitted_at: datetime,
    retention_expires_at: datetime,
    max_attempts: int = 3,
) -> dict[str, Any]:
    """Build the versioned event payload stored in the transactional outbox."""
    return {
        "event_id": event_id,
        "event_type": "sird.task.submitted.v1",
        "task_id": request.task_id,
        "request_id": request.request_id,
        "artifact_ref": request.artifact_ref,
        "policy": dict(request.policy),
        "retention_seconds": request.effective_retention_seconds,
        "max_attempts": max_attempts,
        "submitted_at": submitted_at.isoformat(),
        "retention_expires_at": retention_expires_at.isoformat(),
    }
