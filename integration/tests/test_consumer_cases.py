from __future__ import annotations

from typing import Any, NamedTuple

from sird_workflow.consumer import RabbitMQTaskConsumer, TaskConsumerMessage
from sird_workflow.process_outcome import ProcessOutcome
from sird_workflow.task_event import TaskEvent
from test_consumer_data import _event, _message
from test_consumer_doubles import (
    RecordingDispatcher,
    RecordingProcess,
    _consumer,
)
from test_consumer_outcomes import _failed_outcome, _retrying_outcome
from test_consumer_storage import _engine_with_outboxes


class ConsumerCase(NamedTuple):
    event: TaskEvent
    process: RecordingProcess
    dispatcher: RecordingDispatcher
    commits: list[Any]
    consumer: RabbitMQTaskConsumer


def _case(
    outcome: ProcessOutcome | None,
    *,
    acknowledge_dead_letter: bool,
) -> ConsumerCase:
    return _assemble_case(
        _event(), outcome, acknowledge_dead_letter=acknowledge_dead_letter
    )


def _assemble_case(
    event: TaskEvent,
    outcome: ProcessOutcome | None,
    *,
    acknowledge_dead_letter: bool,
) -> ConsumerCase:
    process = RecordingProcess(outcome)
    engine = _engine_with_outboxes()
    dispatcher = RecordingDispatcher(
        engine, acknowledge_dead_letter=acknowledge_dead_letter
    )
    commits: list[Any] = []
    consumer = _consumer(engine, process, dispatcher, commits)
    return ConsumerCase(event, process, dispatcher, commits, consumer)


def _failed_case(*, acknowledge_dead_letter: bool) -> ConsumerCase:
    event = _event()
    return _case(
        _failed_outcome(event),
        acknowledge_dead_letter=acknowledge_dead_letter,
    )


def _retrying_case() -> ConsumerCase:
    event = _event()
    return _case(
        _retrying_outcome(event),
        acknowledge_dead_letter=True,
    )


def _message_for(case: ConsumerCase) -> TaskConsumerMessage:
    return _message(case.event)
