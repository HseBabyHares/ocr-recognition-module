from __future__ import annotations

from typing import Any, NamedTuple

from sird_workflow.consumer import RabbitMQTaskConsumer
from sird_workflow.task_event import TaskEvent
from test_consumer_data import _event
from test_consumer_outcomes import _retry_outcome, _success_outcome
from test_consumer_safety_helpers import (
    NonPublishingDispatcher,
    RetryProcess,
    TerminalProcess,
    _consumer,
)
from test_consumer_safety_storage import _suppressed_engine


class SafetyCase(NamedTuple):
    event: TaskEvent
    process: Any
    dispatcher: NonPublishingDispatcher
    commits: list[Any]
    consumer: RabbitMQTaskConsumer


def _partition_case() -> SafetyCase:
    event = _event()
    process = RetryProcess(_retry_outcome(event))
    dispatcher = NonPublishingDispatcher()
    commits: list[Any] = []
    consumer = _consumer(process, dispatcher, commits)
    return SafetyCase(event, process, dispatcher, commits, consumer)


def _suppressed_case() -> SafetyCase:
    event = _event()
    engine = _suppressed_engine(event)
    process = TerminalProcess(_success_outcome(event))
    dispatcher = NonPublishingDispatcher()
    commits: list[Any] = []
    return SafetyCase(
        event,
        process,
        dispatcher,
        commits,
        _consumer(process, dispatcher, commits, engine=engine),
    )
