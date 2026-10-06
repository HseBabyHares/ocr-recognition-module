"""Deterministic backoff delays for transient process attempts."""

from __future__ import annotations

from typing import Final

_RETRY_DELAYS: Final[tuple[float, float]] = (1.0, 2.0)


def backoff_seconds(attempt_number: int) -> float:
    """Return the delay after a transient failure on an attempt.

    Attempts one and two may retry after one and two seconds, respectively.
    The third and later attempts are exhausted and return zero, which denotes
    no retry.  This function only calculates a delay; it never sleeps.
    """
    if attempt_number <= 0:
        raise ValueError("attempt_number must be positive")
    if attempt_number > len(_RETRY_DELAYS):
        return 0
    return _RETRY_DELAYS[attempt_number - 1]
