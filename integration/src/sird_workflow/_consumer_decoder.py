"""Validation and decoding of one RabbitMQ delivery."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sird_workflow._consumer_models import TaskConsumerDecision
from sird_workflow._consumer_state import _ConsumerState
from sird_workflow._consumer_tools import _ConsumerTools
from sird_workflow.invalid_task_event_error import InvalidTaskEventError
from sird_workflow.task_event import TaskEvent


def _is_decode_error(error: Exception) -> bool:
    return isinstance(
        error,
        (
            AttributeError,
            InvalidTaskEventError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ),
    )


@dataclass(frozen=True, slots=True)
class _MessageFields:
    """Raw transport fields read from one broker delivery."""

    routing_key: Any
    delivery_tag: Any
    key: Any
    raw_value: Any
    message_id: Any


@dataclass(frozen=True, slots=True)
class _DecodedMessage:
    """Validated transport and task-event values."""

    transport: Any
    event: TaskEvent
    delivery_id: str


def _read_message_fields(message: Any) -> _MessageFields:
    raw_value = _ConsumerTools.optional_message_field(message, "value")
    if raw_value is None:
        raw_value = _ConsumerTools.optional_message_field(message, "body")
    return _MessageFields(
        routing_key=_ConsumerTools.message_field(message, "routing_key"),
        delivery_tag=_ConsumerTools.message_field(message, "delivery_tag"),
        key=_ConsumerTools.optional_message_field(message, "key"),
        raw_value=raw_value,
        message_id=_ConsumerTools.optional_message_field(
            message, "message_id"
        ),
    )


class _ConsumerDecoder(_ConsumerState):
    """Decode transport fields and validate the embedded task event."""

    def _decode_message(self, message: Any) -> _DecodedMessage | None:
        try:
            decoded = self._decode_event(message)
        except Exception as error:
            if _is_decode_error(error):
                return None
            raise
        if decoded is None:
            return None
        event, message_id = decoded
        return _DecodedMessage(
            transport=message,
            event=event,
            delivery_id=message_id or event.event_id,
        )

    def _decode_event(
        self, message: Any
    ) -> tuple[TaskEvent, str | None] | None:
        fields = _read_message_fields(message)
        if not isinstance(fields.routing_key, str) or not fields.routing_key:
            return None
        if not isinstance(fields.delivery_tag, int) or fields.delivery_tag < 0:
            return None
        payload = _ConsumerTools.decode_payload(fields.raw_value)
        event = TaskEvent.decode(payload)
        decoded_key = _ConsumerTools.decode_key(fields.key)
        if decoded_key is not None and decoded_key != event.task_id:
            return None
        if (
            fields.message_id is not None
            and fields.message_id != event.event_id
        ):
            return None
        return event, fields.message_id

    def _decision(self, name: str) -> TaskConsumerDecision:
        return self._decision_type[name]
