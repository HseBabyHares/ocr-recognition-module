from __future__ import annotations

import test_consumer_constants as ConsumerConstants
from sird_workflow.consumer import TaskConsumerDecision
from test_consumer_assertions import _assert_retry_without_commit
from test_consumer_data import _message
from test_consumer_safety_cases import _partition_case, _suppressed_case


def test_partition_retry_blocks_later_offset() -> None:
    case = _partition_case()

    first = case.consumer.handle_message(
        _message(case.event, offset=ConsumerConstants.FIRST_OFFSET)
    )
    later = case.consumer.handle_message(
        _message(case.event, offset=ConsumerConstants.LATER_OFFSET)
    )

    _assert_retry_without_commit(first, case.commits)
    _assert_retry_without_commit(later, case.commits)
    assert case.process.calls == 1


def test_suppressed_result_is_terminal() -> None:
    case = _suppressed_case()
    message = _message(case.event, offset=ConsumerConstants.FIRST_OFFSET)

    decision = case.consumer.handle_message(message)

    assert decision is TaskConsumerDecision.TERMINAL_COMMIT_READY
    assert case.commits == [message]
    assert case.process.calls == 1
    assert case.dispatcher.dispatch_calls == 1
    assert case.dispatcher.published == []
