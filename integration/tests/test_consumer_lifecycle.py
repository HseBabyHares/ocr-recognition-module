from __future__ import annotations

import threading
from types import SimpleNamespace

import test_consumer_constants as ConsumerConstants
from sird_workflow.cancellation import CancellationToken
from sird_workflow.consumer import (
    RabbitMQTaskConsumer,
    TaskConsumerDecision,
)
from test_consumer_assertions import _assert_retry_without_commit
from test_consumer_cases import _case, _message_for
from test_consumer_data import _event, _message
from test_consumer_doubles import (
    BlockingProcess,
    RecordingDispatcher,
    RecordingProcess,
    RecordingRabbitClient,
    _consumer,
)
from test_consumer_outcomes import _cancelled_outcome
from test_consumer_storage import _engine_with_outboxes


def _blocking_case() -> tuple[
    BlockingProcess, list[object], RabbitMQTaskConsumer
]:
    engine = _engine_with_outboxes()
    process = BlockingProcess()
    dispatcher = RecordingDispatcher(engine, acknowledge_dead_letter=True)
    commits: list[object] = []
    consumer = _consumer(engine, process, dispatcher, commits)
    return process, commits, consumer


def _handle_and_append(
    consumer: RabbitMQTaskConsumer,
    decisions: list[TaskConsumerDecision],
) -> None:
    decisions.append(consumer.handle_message(_message(_event())))


def test_cancellation_token_reaches_service() -> None:
    case = _case(_cancelled_outcome(_event()), acknowledge_dead_letter=True)
    token = CancellationToken()

    decision = case.consumer.handle_message(_message_for(case), token)

    assert decision is TaskConsumerDecision.TERMINAL_COMMIT_READY
    assert case.process.cancellation is token


def test_subscribe_registers_revoke_callback() -> None:
    client = RecordingRabbitClient()
    engine = _engine_with_outboxes()
    consumer = _consumer(
        engine,
        RecordingProcess(None),
        RecordingDispatcher(engine, acknowledge_dead_letter=True),
        [],
        client=client,
    )

    consumer.subscribe([ConsumerConstants.TOPIC])

    assert client.subscribed is not None
    topics, options = client.subscribed
    assert topics == [ConsumerConstants.TOPIC]
    assert options["on_revoke"] == consumer._on_revoke


def test_close_cancels_work_and_closes_client() -> None:
    client = RecordingRabbitClient()
    engine = _engine_with_outboxes()
    consumer = _consumer(
        engine,
        RecordingProcess(None),
        RecordingDispatcher(engine, acknowledge_dead_letter=True),
        [],
        client=client,
    )
    token = CancellationToken()
    position = (
        ConsumerConstants.TOPIC,
        ConsumerConstants.PARTITION,
        ConsumerConstants.DELIVERY_TAG,
    )
    consumer._active_cancellations[position] = token

    consumer.close()

    assert token.cancelled
    assert token.terminal is False
    assert client.closed


def test_revoke_cancels_registered_ocr() -> None:
    case = _case(None, acknowledge_dead_letter=True)
    token = CancellationToken()
    position = (
        ConsumerConstants.TOPIC,
        ConsumerConstants.PARTITION,
        ConsumerConstants.DELIVERY_TAG,
    )
    case.consumer._active_cancellations[position] = token

    case.consumer.on_revoke(
        None,
        [SimpleNamespace(topic=position[0], partition=position[1])],
    )

    assert token.cancelled


def test_revoke_requeues_running_ocr() -> None:
    process, commits, consumer = _blocking_case()
    decisions: list[TaskConsumerDecision] = []

    worker = threading.Thread(
        target=_handle_and_append, args=(consumer, decisions)
    )
    worker.start()
    assert process.started.wait(timeout=ConsumerConstants.WAIT_TIMEOUT_SECONDS)
    consumer._on_revoke(
        None,
        [
            SimpleNamespace(
                topic=ConsumerConstants.TOPIC,
                partition=ConsumerConstants.PARTITION,
            )
        ],
    )
    worker.join(timeout=ConsumerConstants.WAIT_TIMEOUT_SECONDS)
    assert not worker.is_alive()
    _assert_retry_without_commit(decisions[0], commits)
