from __future__ import annotations

from typing import Any

from sird_workflow.db import (
    Base,
    TaskRecord,
    TaskResultOutbox,
    session_factory,
)
from sird_workflow.task_event import TaskEvent
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool


def _suppressed_engine(event: TaskEvent) -> Any:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
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
                event_id=f"{event.event_id}:result",
                task_id=event.task_id,
                source_event_id=event.event_id,
                request_id=event.request_id,
                topic="sird.task.result.v1",
                payload={
                    "event_id": f"{event.event_id}:result",
                    "task_id": event.task_id,
                    "request_id": event.request_id,
                },
                created_at=now,
                suppressed_at=now,
                suppression_reason="retention_expired",
            )
        )
    return engine
