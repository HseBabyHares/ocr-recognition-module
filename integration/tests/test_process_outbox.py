from __future__ import annotations

from datetime import UTC, datetime, timedelta

from process_outbox_support import (
    OutboxConfig,
    RecordingDeadLetterPublisher,
    RecordingResultProducer,
    RetryScenario,
    engine_with_pending_rows,
    expire_result,
)
from sird_workflow.db import (
    TaskDeadLetterOutbox,
    TaskResultOutbox,
    session_factory,
)
from sird_workflow.process_outbox import ProcessOutboxDispatcher
from sqlalchemy import select
from sqlalchemy.engine import Engine


def test_failed_rows_retry_stable_ids() -> None:
    RetryScenario().run()


def test_negative_dead_letter_ack() -> None:
    engine = engine_with_pending_rows()
    dispatcher = ProcessOutboxDispatcher(
        engine,
        RecordingResultProducer(),
        RecordingDeadLetterPublisher(acknowledged=False),
    )
    report = dispatcher.dispatch_pending(limit=1)
    assert report.dead_letter_attempted == 1
    assert report.dead_letter_acknowledged == 0
    assert report.dead_letter_failed == 1
    with session_factory(engine)() as session:
        row = session.scalar(select(TaskDeadLetterOutbox))
        assert row is not None
        assert row.acknowledged_at is None


def _add_later_pending_rows(engine: Engine) -> None:
    now = datetime.now(UTC)
    with session_factory(engine)() as session, session.begin():
        session.add(
            TaskResultOutbox(
                event_id="result-2",
                task_id=OutboxConfig.task_id,
                source_event_id="submitted-2",
                request_id=OutboxConfig.request_id,
                topic="sird.task.result.v1",
                payload={OutboxConfig.event_id_key: "result-2"},
                created_at=now + timedelta(seconds=1),
            )
        )
        session.add(
            TaskDeadLetterOutbox(
                event_id="dead-letter-2",
                task_id=OutboxConfig.task_id,
                source_event_id="submitted-2",
                request_id=OutboxConfig.request_id,
                topic="sird.task.dead-letter.v1",
                payload={OutboxConfig.event_id_key: "dead-letter-2"},
                created_at=now + timedelta(seconds=1),
            )
        )


def _assert_limited_dispatch(engine: Engine) -> None:
    result_producer = RecordingResultProducer()
    dead_letter_publisher = RecordingDeadLetterPublisher(acknowledged=True)
    report = ProcessOutboxDispatcher(
        engine, result_producer, dead_letter_publisher
    ).dispatch_pending(limit=1)
    assert report.result_attempted == 1
    assert report.dead_letter_attempted == 1
    assert [
        call["payload"][OutboxConfig.event_id_key]
        for call in result_producer.calls
    ] == ["result-1"]
    assert [event.event_id for event in dead_letter_publisher.events] == [
        "dead-letter-1"
    ]


def test_limit_bounds_each_pending_outbox() -> None:
    engine = engine_with_pending_rows()
    _add_later_pending_rows(engine)
    _assert_limited_dispatch(engine)


def _assert_suppressed_row(engine: Engine) -> None:
    with session_factory(engine)() as session:
        result_row = session.scalar(select(TaskResultOutbox))
        assert result_row is not None
        assert result_row.published_at is None
        assert result_row.suppressed_at is not None
        assert result_row.suppression_reason == "retention_expired"


def test_expired_result_suppressed() -> None:
    engine = engine_with_pending_rows()
    expire_result(engine)
    producer = RecordingResultProducer()
    dispatcher = ProcessOutboxDispatcher(
        engine,
        producer,
        RecordingDeadLetterPublisher(acknowledged=True),
    )
    report = dispatcher.dispatch_pending(limit=1)
    assert report.result_attempted == 1
    assert report.result_published == 0
    assert report.result_failed == 0
    assert not producer.calls
    _assert_suppressed_row(engine)
    dispatcher.dispatch_pending(limit=1)
    assert not producer.calls
