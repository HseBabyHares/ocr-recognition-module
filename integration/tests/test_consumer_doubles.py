from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any, cast

import test_consumer_constants as ConsumerConstants
from sird_workflow import (
    cancellation,
    consumer,
    db,
    ocr_outcome,
    process_outbox,
)
from sird_workflow.process_outcome import ProcessOutcome
from sird_workflow.task_event import TaskEvent
from sqlalchemy import update

CancellationToken = cancellation.CancellationToken
RabbitMQConsumerConfig = consumer.RabbitMQConsumerConfig
RabbitMQTaskConsumer = consumer.RabbitMQTaskConsumer
OcrOutcome = ocr_outcome.OcrOutcome
ProcessOutboxDispatcher = process_outbox.ProcessOutboxDispatcher

TaskDeadLetterOutbox = db.TaskDeadLetterOutbox
TaskResultOutbox = db.TaskResultOutbox
session_factory = db.session_factory


class RecordingProcess:
    def __init__(self, outcome: ProcessOutcome | None) -> None:
        self.outcome = outcome
        self.process_calls = 0
        self.reconcile_calls = 0
        self.cancellation: CancellationToken | None = None

    def reconcile_event(self, _event: TaskEvent) -> ProcessOutcome | None:
        self.reconcile_calls += 1
        reconciled = self.outcome if self.reconcile_calls > 1 else None
        return reconciled

    def process_event(
        self,
        _event: TaskEvent,
        _worker_id: str,
        _delivery_id: str,
        *,
        cancellation: CancellationToken | None = None,
    ) -> ProcessOutcome:
        self.cancellation = cancellation
        self.process_calls += 1
        assert self.outcome is not None
        return self.outcome


class BlockingProcess:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.cancellation: CancellationToken | None = None

    def process_event(
        self,
        event: TaskEvent,
        _worker_id: str,
        _delivery_id: str,
        *,
        cancellation: CancellationToken,
    ) -> ProcessOutcome:
        self.cancellation = cancellation
        self.started.set()
        if (
            cancellation.wait(
                timeout=ConsumerConstants.BLOCKING_TIMEOUT_SECONDS
            )
            is False
        ):
            raise TimeoutError("cancellation callback did not fire")
        return ProcessOutcome(
            task_id=event.task_id,
            event_id=event.event_id,
            status="retrying",
            outcome=OcrOutcome.TRANSIENT.value,
            attempt_number=1,
        )


class RecordingDispatcher:
    def __init__(self, engine: Any, *, acknowledge_dead_letter: bool) -> None:
        self._session_factory = session_factory(engine)
        self.acknowledge_dead_letter = acknowledge_dead_letter
        self.calls = 0

    def dispatch_pending(self) -> None:
        self.calls += 1
        with self._session_factory() as session, session.begin():
            session.execute(
                update(TaskResultOutbox).values(published_at=datetime.now(UTC))
            )
            if self.acknowledge_dead_letter:
                session.execute(
                    update(TaskDeadLetterOutbox).values(
                        acknowledged_at=datetime.now(UTC)
                    )
                )


class RecordingRabbitClient:
    def __init__(self) -> None:
        self.subscribed: tuple[Any, dict[str, Any]] | None = None
        self.closed = False

    def subscribe(self, topics: Any, **kwargs: Any) -> None:
        self.subscribed = (topics, kwargs)

    def close(self) -> None:
        self.closed = True


def _client_or_default(client: Any | None) -> Any:
    if client is not None:
        return client
    return object()


def _consumer(
    engine: Any,
    process: Any,
    dispatcher: RecordingDispatcher,
    commits: list[Any],
    *,
    client: Any | None = None,
) -> RabbitMQTaskConsumer:
    return RabbitMQTaskConsumer(
        RabbitMQConsumerConfig("amqps://localhost:5671/sird"),
        process,
        cast(ProcessOutboxDispatcher, dispatcher),
        commits.append,
        worker_id=ConsumerConstants.WORKER_ID,
        engine=engine,
        consumer=_client_or_default(client),
    )
