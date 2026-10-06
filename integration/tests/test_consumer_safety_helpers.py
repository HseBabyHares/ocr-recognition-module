from __future__ import annotations

from typing import Any

import test_consumer_constants as ConsumerConstants
from sird_workflow.consumer import RabbitMQConsumerConfig, RabbitMQTaskConsumer
from sird_workflow.process_outcome import ProcessOutcome
from sird_workflow.task_event import TaskEvent


class RetryProcess:
    def __init__(self, outcome: ProcessOutcome) -> None:
        self.outcome = outcome
        self.calls = 0

    def process_event(
        self,
        _event: TaskEvent,
        _worker_id: str,
        _delivery_id: str,
        *,
        cancellation: Any | None = None,
    ) -> ProcessOutcome:
        self.calls += 1
        return self.outcome


class TerminalProcess:
    def __init__(self, outcome: ProcessOutcome) -> None:
        self.outcome = outcome
        self.calls = 0

    def process_event(
        self,
        _event: TaskEvent,
        _worker_id: str,
        _delivery_id: str,
        *,
        cancellation: Any | None = None,
    ) -> ProcessOutcome:
        self.calls += 1
        return self.outcome


class NonPublishingDispatcher:
    def __init__(self) -> None:
        self.dispatch_calls = 0
        self.published: list[str] = []

    def dispatch_pending(self) -> None:
        self.dispatch_calls += 1


def _consumer(
    process: Any,
    dispatcher: Any,
    commits: list[Any],
    *,
    engine: Any | None = None,
) -> RabbitMQTaskConsumer:
    return RabbitMQTaskConsumer(
        RabbitMQConsumerConfig("amqps://localhost:5671/sird"),
        process,
        dispatcher,
        commits.append,
        worker_id=ConsumerConstants.WORKER_ID,
        engine=engine,
        consumer=object(),
    )
