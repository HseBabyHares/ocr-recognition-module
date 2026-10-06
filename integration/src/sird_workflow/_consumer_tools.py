"""Message transport normalization shared by consumer helpers."""

from __future__ import annotations

import inspect
import json
from collections.abc import Mapping
from typing import Any

from sird_workflow.task_event import TaskEvent


class _ConsumerTools:
    """Small transport helpers shared by consumer operation mixins."""

    @classmethod
    def message_field(cls, message: Any, name: str) -> Any:
        field_value = getattr(message, name)
        return field_value() if callable(field_value) else field_value

    @classmethod
    def optional_message_field(cls, message: Any, name: str) -> Any:
        try:
            return cls.message_field(message, name)
        except AttributeError:
            return None

    @classmethod
    def message_position(cls, message: Any) -> str | None:
        fields = _read_position_fields(message)
        if fields is None:
            return None
        route, message_id, delivery_tag = fields
        if isinstance(route, str) and route:
            return route
        if isinstance(message_id, str) and message_id:
            return message_id
        if isinstance(delivery_tag, int) and delivery_tag >= 0:
            return f"delivery:{delivery_tag}"
        return None

    @classmethod
    def decode_key(cls, key: Any) -> str | None:
        if isinstance(key, bytes):
            return key.decode("utf-8")
        return key if isinstance(key, str) else None

    @classmethod
    def decode_payload(cls, raw_payload: Any) -> Mapping[str, Any]:
        if isinstance(raw_payload, Mapping):
            return raw_payload
        if isinstance(raw_payload, bytes):
            raw_payload = raw_payload.decode("utf-8")
        if isinstance(raw_payload, str):
            decoded = json.loads(raw_payload)
            if isinstance(decoded, Mapping):
                return decoded
        raise TypeError("RabbitMQ task payload must be a JSON object")

    @classmethod
    def event_payload(cls, event: TaskEvent) -> dict[str, Any]:
        return {
            "event_type": event.event_type,
            "event_id": event.event_id,
            "task_id": event.task_id,
            "request_id": event.request_id,
            "artifact_ref": event.artifact_ref,
            "policy": dict(event.policy),
            "retention_seconds": event.retention_seconds,
            "max_attempts": event.max_attempts,
            "submitted_at": event.submitted_at.isoformat(),
            "retention_expires_at": event.retention_expires_at.isoformat(),
        }

    @classmethod
    async def await_message_action(
        cls, message: Any, action: str, **kwargs: Any
    ) -> None:
        method = getattr(message, action, None)
        if not callable(method):
            raise TypeError(f"RabbitMQ delivery does not expose {action}")
        action_result = method(**kwargs)
        if inspect.isawaitable(action_result):
            await action_result


def _read_position_fields(
    message: Any,
) -> tuple[Any, Any, Any] | None:
    try:
        return _read_position_values(message)
    except (AttributeError, TypeError, ValueError):
        return None


def _read_position_values(message: Any) -> tuple[Any, Any, Any]:
    route = _ConsumerTools.optional_message_field(message, "routing_key")
    if route is None:
        route = _ConsumerTools.optional_message_field(message, "topic")
    if isinstance(route, str) and route:
        return route, None, None
    return (
        route,
        _ConsumerTools.optional_message_field(message, "message_id"),
        _ConsumerTools.optional_message_field(message, "delivery_tag"),
    )
