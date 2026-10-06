from __future__ import annotations

from typing import Any

from sird_workflow.consumer import TaskConsumerDecision


def _assert_retry_without_commit(decision: Any, commits: list[Any]) -> None:
    assert decision is TaskConsumerDecision.RETRY_WITHOUT_COMMIT
    assert commits == []


def _assert_terminal_commit(
    decision: Any, commits: list[Any], message: Any
) -> None:
    assert decision is TaskConsumerDecision.TERMINAL_COMMIT_READY
    assert commits == [message]


def _assert_invalid_without_processing(
    decision: Any, process_calls: int, commits: list[Any]
) -> None:
    assert decision is TaskConsumerDecision.INVALID_EVENT
    assert process_calls == 0
    assert commits == []
