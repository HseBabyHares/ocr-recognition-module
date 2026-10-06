from __future__ import annotations

from typing import Any


def check_equal(actual: Any, expected: Any) -> None:
    assert actual == expected


def check_true(condition: Any) -> None:
    assert condition


def check_false(condition: Any) -> None:
    assert not condition


def check_present(candidate: Any) -> None:
    assert candidate is not None


def check_absent(candidate: Any) -> None:
    assert candidate is None


def check_greater(actual: Any, expected: Any) -> None:
    assert actual > expected


def append_call_result(calls: list[Any], call: Any) -> None:
    calls.append(call())
