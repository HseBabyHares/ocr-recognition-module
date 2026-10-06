from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import test_consumer_constants as ConsumerConstants
from sird_workflow.consumer import TaskConsumerMessage
from sird_workflow.task_event import TaskEvent
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(
    _type: JSONB, _compiler: Any, **_kwargs: Any
) -> str:
    return "JSON"


def _event(*, event_id: str = ConsumerConstants.EVENT_ID) -> TaskEvent:
    now = datetime.now(UTC)
    return TaskEvent(
        event_id=event_id,
        task_id=ConsumerConstants.TASK_ID,
        request_id=ConsumerConstants.REQUEST_ID,
        artifact_ref=ConsumerConstants.ARTIFACT_REF,
        policy={},
        retention_seconds=ConsumerConstants.RETENTION_SECONDS,
        max_attempts=ConsumerConstants.MAX_ATTEMPTS,
        submitted_at=now,
        retention_expires_at=now + timedelta(hours=1),
    )


def _payload(event: TaskEvent) -> dict[str, Any]:
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


def _message(
    event: TaskEvent, *, offset: int = ConsumerConstants.DELIVERY_TAG
) -> TaskConsumerMessage:
    return TaskConsumerMessage(
        routing_key=ConsumerConstants.TOPIC,
        delivery_tag=offset,
        key=event.task_id,
        value=_payload(event),
        message_id=event.event_id,
    )
