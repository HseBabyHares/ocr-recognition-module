from __future__ import annotations

from typing import Any

import test_consumer_constants as ConsumerConstants
from sird_workflow.db import (
    Base,
    TaskDeadLetterOutbox,
    TaskRecord,
    TaskResultOutbox,
    session_factory,
)
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from test_consumer_data import _event


def _engine_with_outboxes() -> Any:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    event = _event()
    now = event.submitted_at
    with session_factory(engine)() as session, session.begin():
        session.add(
            TaskRecord(
                task_id=event.task_id,
                request_id=event.request_id,
                artifact_ref=event.artifact_ref,
                policy={},
                request_fingerprint="fingerprint-1",
                status="succeeded",
                retention_seconds=event.retention_seconds,
                retention_expires_at=event.retention_expires_at,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            TaskResultOutbox(
                event_id=ConsumerConstants.RESULT_EVENT_ID,
                task_id=event.task_id,
                source_event_id=event.event_id,
                request_id=event.request_id,
                topic="sird.task.result.v1",
                payload={"event_id": ConsumerConstants.RESULT_EVENT_ID},
                created_at=now,
            )
        )
        session.add(
            TaskDeadLetterOutbox(
                event_id=ConsumerConstants.DEAD_LETTER_EVENT_ID,
                task_id=event.task_id,
                source_event_id=event.event_id,
                request_id=event.request_id,
                topic="sird.task.dead-letter.v1",
                payload={"event_id": ConsumerConstants.DEAD_LETTER_EVENT_ID},
                created_at=now,
            )
        )
    return engine
