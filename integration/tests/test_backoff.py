from __future__ import annotations

import pytest
from sird_workflow.backoff import backoff_seconds


@pytest.mark.parametrize(
    ("attempt_number", "expected_delay"),
    ((1, 1.0), (2, 2.0), (3, 0), (4, 0)),
)
def test_backoff_seconds_is_bounded(
    attempt_number: int, expected_delay: float
) -> None:
    assert backoff_seconds(attempt_number) == expected_delay


@pytest.mark.parametrize("attempt_number", (0, -1))
def test_backoff_rejects_non_positive(
    attempt_number: int,
) -> None:
    with pytest.raises(ValueError, match="attempt_number must be positive"):
        backoff_seconds(attempt_number)
