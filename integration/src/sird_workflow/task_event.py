"""Decoded submitted task event value object."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sird_workflow.invalid_task_event_error import InvalidTaskEventError

TASK_EVENT_TYPE = "sird.task.submitted.v1"
REQUIRED_TASK_EVENT_FIELDS = (
    "event_id",
    "task_id",
    "request_id",
    "artifact_ref",
    "policy",
    "retention_seconds",
    "max_attempts",
    "submitted_at",
    "retention_expires_at",
)


class _TaskEventCodec:
    """Validate and decode versioned task event payloads."""

    @classmethod
    def decode_datetime(cls, raw_value: Any) -> datetime:
        if not isinstance(raw_value, str):
            raise TypeError("datetime must be an ISO string")
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed

    @classmethod
    def require_text_fields(cls, event: TaskEvent) -> None:
        for field_name in (
            "event_id",
            "task_id",
            "request_id",
            "artifact_ref",
        ):
            field_value = getattr(event, field_name)
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

    @classmethod
    def validate_event(cls, event: TaskEvent) -> None:
        cls.require_text_fields(event)
        if event.event_type != TASK_EVENT_TYPE:
            raise InvalidTaskEventError(
                f"unsupported task event type: {event.event_type!r}"
            )
        if not isinstance(event.policy, Mapping):
            raise TypeError("policy must be a mapping")
        if event.retention_seconds <= 0 or event.max_attempts <= 0:
            raise ValueError(
                "retention_seconds and max_attempts must be positive"
            )

    @classmethod
    def validate_payload_mapping(cls, payload: Mapping[str, Any]) -> None:
        if not isinstance(payload, Mapping):
            raise TypeError("task event payload must be a mapping")

    @classmethod
    def validate_payload_type(cls, payload: Mapping[str, Any]) -> None:
        if payload.get("event_type") != TASK_EVENT_TYPE:
            raise InvalidTaskEventError(
                "only sird.task.submitted.v1 is accepted"
            )

    @classmethod
    def decode_event(
        cls, event_class: type[TaskEvent], payload: Mapping[str, Any]
    ) -> TaskEvent:
        try:
            return event_class(
                event_id=payload["event_id"],
                task_id=payload["task_id"],
                request_id=payload["request_id"],
                artifact_ref=payload["artifact_ref"],
                policy=dict(payload["policy"]),
                retention_seconds=int(payload["retention_seconds"]),
                max_attempts=int(payload["max_attempts"]),
                submitted_at=cls.decode_datetime(payload["submitted_at"]),
                retention_expires_at=cls.decode_datetime(
                    payload["retention_expires_at"]
                ),
            )
        except (TypeError, ValueError) as exc:
            raise InvalidTaskEventError(
                "task event has invalid fields"
            ) from exc


@dataclass(frozen=True, slots=True)
class TaskEvent:
    """Decoded ``sird.task.submitted.v1`` event."""

    event_id: str
    task_id: str
    request_id: str
    artifact_ref: str
    policy: Mapping[str, Any]
    retention_seconds: int
    max_attempts: int
    submitted_at: datetime
    retention_expires_at: datetime
    event_type: str = TASK_EVENT_TYPE

    def __post_init__(self) -> None:
        _TaskEventCodec.validate_event(self)

    @classmethod
    def decode(cls, payload: Mapping[str, Any]) -> TaskEvent:
        """Decode only the currently supported versioned event payload."""
        _TaskEventCodec.validate_payload_mapping(payload)
        _TaskEventCodec.validate_payload_type(payload)
        missing = [
            field_name
            for field_name in REQUIRED_TASK_EVENT_FIELDS
            if field_name not in payload
        ]
        if missing:
            missing_fields = ", ".join(missing)
            raise InvalidTaskEventError(
                f"task event is missing required fields: {missing_fields}"
            )
        return _TaskEventCodec.decode_event(cls, payload)

    from_payload = decode
