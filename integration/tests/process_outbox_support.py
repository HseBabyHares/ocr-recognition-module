from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import process_tests_helpers as helpers
from sird_workflow import db, dead_letter, process_outbox
from sqlalchemy import create_engine, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

assert_outbox_retry_report = helpers.assert_outbox_retry_report
assert_outbox_retry_state = helpers.assert_outbox_retry_state
assert_outbox_success_report = helpers.assert_outbox_success_report
assert_outbox_success_state = helpers.assert_outbox_success_state
Base = db.Base
TaskDeadLetterOutbox = db.TaskDeadLetterOutbox
TaskRecord = db.TaskRecord
TaskResultOutbox = db.TaskResultOutbox
BrokerAcknowledgement = dead_letter.BrokerAcknowledgement
DeadLetterEvent = dead_letter.DeadLetterEvent
ProcessOutboxDispatcher = process_outbox.ProcessOutboxDispatcher


class OutboxConfig:
    task_id = "task-1"
    request_id = "request-1"
    retention_seconds = 3600
    payload_key = "payload"
    event_id_key = "event_id"


def expire_result(engine: Engine) -> None:
    now = datetime.now(UTC)
    with Session(engine) as session, session.begin():
        session.execute(
            update(TaskRecord)
            .where(TaskRecord.task_id == OutboxConfig.task_id)
            .values(retention_expires_at=now - timedelta(seconds=1))
        )


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(
    _type: JSONB, _compiler: Any, **_kwargs: Any
) -> str:
    return "JSON"


class RecordingResultProducer:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, Any]] = []

    def publish(
        self, *, topic: str, key: str, payload: Mapping[str, Any]
    ) -> None:
        self.calls.append({"topic": topic, "key": key, "payload": payload})
        if self.fail:
            raise RuntimeError("result broker unavailable")


class RecordingDeadLetterPublisher:
    def __init__(self, *, acknowledged: bool) -> None:
        self.acknowledged = acknowledged
        self.events: list[DeadLetterEvent] = []

    def publish(self, event: DeadLetterEvent) -> BrokerAcknowledgement:
        self.events.append(event)
        return BrokerAcknowledgement(
            event_id=event.event_id,
            acknowledged=self.acknowledged,
        )


def engine_with_pending_rows() -> Engine:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)
    with Session(engine) as session, session.begin():
        session.add(
            TaskRecord(
                task_id=OutboxConfig.task_id,
                request_id=OutboxConfig.request_id,
                artifact_ref="artifact-1",
                policy={},
                request_fingerprint="fingerprint-1",
                status="succeeded",
                retention_seconds=OutboxConfig.retention_seconds,
                retention_expires_at=now + timedelta(hours=1),
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            TaskResultOutbox(
                event_id="result-1",
                task_id=OutboxConfig.task_id,
                source_event_id="submitted-1",
                request_id=OutboxConfig.request_id,
                topic="sird.task.result.v1",
                payload={OutboxConfig.event_id_key: "result-1", "value": "ok"},
                created_at=now,
            )
        )
        session.add(
            TaskDeadLetterOutbox(
                event_id="dead-letter-1",
                task_id=OutboxConfig.task_id,
                source_event_id="submitted-1",
                request_id=OutboxConfig.request_id,
                topic="sird.task.dead-letter.v1",
                payload={
                    OutboxConfig.event_id_key: "dead-letter-1",
                    "reason": "failed",
                },
                created_at=now,
            )
        )
    return engine


class RetryScenario:
    def __init__(self) -> None:
        self.engine = engine_with_pending_rows()
        self.first_result = RecordingResultProducer(fail=True)
        self.first_dead_letter = RecordingDeadLetterPublisher(
            acknowledged=False
        )
        self.retry_result = RecordingResultProducer()
        self.retry_dead_letter = RecordingDeadLetterPublisher(
            acknowledged=True
        )

    def run(self) -> None:
        dispatcher = ProcessOutboxDispatcher(
            self.engine, self.first_result, self.first_dead_letter
        )
        initial_report = dispatcher.dispatch_pending(limit=1)
        self._check_retry(initial_report)
        retry_dispatcher = ProcessOutboxDispatcher(
            self.engine, self.retry_result, self.retry_dead_letter
        )
        retry_report = retry_dispatcher.dispatch_pending(limit=1)
        self._check_success(retry_report)

    def _check_retry(self, report: Any) -> None:
        assert_outbox_retry_report(report)
        with Session(self.engine) as session:
            result_row = session.scalar(select(TaskResultOutbox))
            dead_letter_row = session.scalar(select(TaskDeadLetterOutbox))
        assert_outbox_retry_state(result_row, dead_letter_row)

    def _check_success(self, report: Any) -> None:
        assert_outbox_success_report(report)
        assert (
            self.first_dead_letter.events[0].event_id
            == self.retry_dead_letter.events[0].event_id
        )
        first_payload = self.first_result.calls[0][OutboxConfig.payload_key]
        retry_payload = self.retry_result.calls[0][OutboxConfig.payload_key]
        assert (
            first_payload[OutboxConfig.event_id_key]
            == retry_payload[OutboxConfig.event_id_key]
        )
        assert self.retry_result.calls[0]["key"] == OutboxConfig.task_id
        with Session(self.engine) as session:
            result_row = session.scalar(select(TaskResultOutbox))
            dead_letter_row = session.scalar(select(TaskDeadLetterOutbox))
        assert_outbox_success_state(result_row, dead_letter_row)
