"""Typed public request and response models for the task workflow."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

_RETENTION_HOURS = 12
_RESULT_FIELD_NAME = "result"
_RESULT_FIELD_NAMES = (
    _RESULT_FIELD_NAME,
    "created_at",
    "updated_at",
    "retention_expires_at",
    "expired",
)
DEFAULT_RETENTION_SECONDS = _RETENTION_HOURS * 60 * 60


class _ResultAliasMixin:
    __slots__ = ("_payload",)
    _payload: Mapping[str, Any] | None

    @property
    def payload(self) -> Mapping[str, Any] | None:
        """Return the result payload."""
        return self._payload


type.__setattr__(
    _ResultAliasMixin,
    "result",
    property(_ResultAliasMixin.payload.fget),
)


def _require_text(candidate: str, name: str) -> str:
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return candidate


def _result_values(
    positional: tuple[object, ...],
    options: Mapping[str, object],
) -> tuple[object, ...]:
    result_arguments = dict(
        zip(_RESULT_FIELD_NAMES, positional, strict=False),
    )
    result_arguments.update(options)
    result_fields = tuple(
        result_arguments.pop(field_name) for field_name in _RESULT_FIELD_NAMES
    )
    if result_arguments:
        raise TypeError(
            f"unexpected keyword argument: {next(iter(result_arguments))}"
        )
    return result_fields


@dataclass(frozen=True, slots=True)
class SubmitRequest:
    """A backend request to create or reuse one durable task."""

    artifact_ref: str
    request_id: str
    task_id: str = field(default_factory=lambda: str(uuid4()))
    policy: Mapping[str, Any] = field(default_factory=dict)
    retention_seconds: int | None = None

    def __post_init__(self) -> None:
        _require_text(self.task_id, "task_id")
        _require_text(self.request_id, "request_id")
        artifact_ref = _require_text(self.artifact_ref, "artifact_ref")
        if any(character.isspace() for character in artifact_ref) or any(
            marker in artifact_ref for marker in ("/", "\\", "://")
        ):
            raise ValueError(
                "artifact_ref must be an opaque capability, not a URL or path"
            )
        if self.retention_seconds is not None and self.retention_seconds <= 0:
            raise ValueError("retention_seconds must be positive")

    @property
    def effective_retention_seconds(self) -> int:
        return self.retention_seconds or DEFAULT_RETENTION_SECONDS


@dataclass(frozen=True, slots=True)
class TaskSubmission:
    """The acknowledgement returned only after task-event publication."""

    task_id: str
    request_id: str
    status: str
    submitted_at: datetime
    retention_expires_at: datetime


@dataclass(frozen=True, slots=True)
class TaskStatus:
    """Current durable task state."""

    task_id: str
    request_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    retention_expires_at: datetime


@dataclass(frozen=True, slots=True, init=False)
class TaskResult(_ResultAliasMixin):
    """Durable result state, with expired payloads withheld from callers."""

    task_id: str
    request_id: str
    status: str
    result_payload: Mapping[str, Any] | None
    created_at: datetime
    updated_at: datetime
    retention_expires_at: datetime
    expired: bool

    def __init__(
        self,
        task_id: str,
        request_id: str,
        status: str,
        *positional: object,
        **options: object,
    ) -> None:
        result_fields = _result_values(positional, options)
        object.__setattr__(self, "task_id", task_id)
        object.__setattr__(self, "request_id", request_id)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "_payload", result_fields[0])
        for field_name, field_value in zip(
            _RESULT_FIELD_NAMES[1:], result_fields[1:], strict=True
        ):
            object.__setattr__(self, field_name, field_value)
