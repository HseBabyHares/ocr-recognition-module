from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from process_tests_helpers import assert_task_outbox_reports
from sird_workflow.db import Base, TaskOutbox, TaskRecord
from sird_workflow.outbox import TaskOutboxDispatcher
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

TASK_ID = "task-1"
REQUEST_ID = "request-1"
EVENT_ID = "event-1"
TOPIC = "sird.task.v1"
RETENTION_SECONDS = 3600


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(
    _type: JSONB, _compiler: Any, **_kwargs: Any
) -> str:
    return "JSON"


class RecordingProducer:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, Any]] = []

    def publish(
        self, *, topic: str, key: str, payload: Mapping[str, Any]
    ) -> None:
        self.calls.append({"topic": topic, "key": key, "payload": payload})
        if self.fail:
            raise RuntimeError("broker unavailable")


def _engine_with_pending_row() -> tuple[Any, str]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)
    with Session(engine) as session, session.begin():
        session.add(
            TaskRecord(
                task_id=TASK_ID,
                request_id=REQUEST_ID,
                artifact_ref="v1.one",
                policy={"mode": "strict"},
                request_fingerprint="fingerprint",
                status="queued",
                retention_seconds=RETENTION_SECONDS,
                retention_expires_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            TaskOutbox(
                event_id=EVENT_ID,
                task_id=TASK_ID,
                request_id=REQUEST_ID,
                topic=TOPIC,
                payload={"event_id": EVENT_ID, "task_id": TASK_ID},
                created_at=now,
            )
        )
    return engine, EVENT_ID


def _assert_published(engine: Any, event_id: str) -> None:
    with Session(engine) as session:
        published = session.scalar(
            select(TaskOutbox).where(TaskOutbox.event_id == event_id)
        )
        assert published is not None
        assert published.published_at is not None


def _assert_retry_reports(engine: Any, failing: RecordingProducer) -> None:
    first = TaskOutboxDispatcher(engine, failing).dispatch_pending(limit=1)
    succeeding = RecordingProducer()
    second = TaskOutboxDispatcher(engine, succeeding).dispatch_pending(limit=1)
    assert_task_outbox_reports(first, second)
    assert succeeding.calls == [
        {
            "topic": TOPIC,
            "key": TASK_ID,
            "payload": {"event_id": EVENT_ID, "task_id": TASK_ID},
        }
    ]


def test_failed_publication_retry_marks_published() -> None:
    engine, event_id = _engine_with_pending_row()
    _assert_retry_reports(engine, RecordingProducer(fail=True))
    _assert_published(engine, event_id)
