from __future__ import annotations

from typing import cast

import pytest
import test_consumer_constants as ConsumerConstants
from sird_workflow.consumer import (
    RabbitMQConsumerConfig,
    TaskConsumerDecision,
    TaskConsumerMessage,
)
from test_consumer_assertions import (
    _assert_invalid_without_processing,
    _assert_retry_without_commit,
    _assert_terminal_commit,
)
from test_consumer_cases import (
    _case,
    _failed_case,
    _message_for,
    _retrying_case,
)
from test_consumer_data import _event, _payload
from test_consumer_outcomes import _terminal_outcome


def test_dead_letter_ack_required_before_commit() -> None:
    case = _failed_case(acknowledge_dead_letter=False)
    decision = case.consumer.handle_message(_message_for(case))

    _assert_retry_without_commit(decision, case.commits)
    assert case.dispatcher.calls == 1


def test_result_and_dead_letter_ack_allow_commit() -> None:
    case = _failed_case(acknowledge_dead_letter=True)
    message = _message_for(case)
    decision = case.consumer.handle_message(message)

    _assert_terminal_commit(decision, case.commits, message)


def test_retrying_outcome_never_commits() -> None:
    case = _retrying_case()
    decision = case.consumer.handle_message(_message_for(case))

    _assert_retry_without_commit(decision, case.commits)
    assert case.dispatcher.calls == 0


def test_terminal_redelivery_reconciles_once() -> None:
    case = _case(
        _terminal_outcome(_event()),
        acknowledge_dead_letter=True,
    )
    message = _message_for(case)

    first = case.consumer.handle_message(message)
    second = case.consumer.handle_message(message)

    assert first is TaskConsumerDecision.TERMINAL_COMMIT_READY
    assert second is TaskConsumerDecision.TERMINAL_COMMIT_READY
    assert case.process.process_calls == 1
    assert len(case.commits) == 2


def test_invalid_version_is_rejected() -> None:
    case = _case(None, acknowledge_dead_letter=True)
    message = _message_for(case)
    invalid = TaskConsumerMessage(
        routing_key=message.routing_key,
        delivery_tag=message.delivery_tag,
        message_id=message.message_id,
        key=message.key,
        value=cast(
            dict[str, object],
            {**_payload(case.event), "event_type": "sird.task.submitted.v2"},
        ),
    )

    decision = case.consumer.handle_message(invalid)

    _assert_invalid_without_processing(
        decision, case.process.process_calls, case.commits
    )


def test_consumer_enforces_tls_and_prefetch() -> None:
    config = RabbitMQConsumerConfig(
        "amqps://localhost:5671/sird",
        prefetch_count=ConsumerConstants.PREFETCH_COUNT,
    )

    assert config.prefetch_count == ConsumerConstants.PREFETCH_COUNT
    with pytest.raises(ValueError, match="TLS"):
        RabbitMQConsumerConfig("amqp://localhost:5672/sird")


def test_message_key_must_match_task_id() -> None:
    case = _case(None, acknowledge_dead_letter=True)
    message = _message_for(case)
    invalid = TaskConsumerMessage(
        routing_key=message.routing_key,
        delivery_tag=message.delivery_tag,
        message_id=message.message_id,
        key="another-task",
        value=cast(dict[str, object], getattr(message, "value", None)),
    )

    decision = case.consumer.handle_message(invalid)

    _assert_invalid_without_processing(
        decision, case.process.process_calls, case.commits
    )
