"""Validation helpers for attempt-budget state."""

from typing import Any


def require_text(candidate: str, field_name: str) -> str:
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return candidate


def _validate_max_attempts(max_attempts: int) -> None:
    if max_attempts <= 0:
        raise ValueError("max_attempts must be positive")


def _validate_attempts_used(budget: Any) -> None:
    attempts_used = budget.attempts_used
    if not 0 <= attempts_used <= budget.max_attempts:
        raise ValueError("attempts_used must be between zero and max_attempts")


def _validate_active_lease(budget: Any) -> None:
    lease = budget.active_lease
    if lease is not None and lease.task_id != budget.task_id:
        raise ValueError("active lease task_id does not match budget task_id")


def validate_budget(budget: Any) -> None:
    require_text(budget.task_id, "task_id")
    _validate_max_attempts(budget.max_attempts)
    _validate_attempts_used(budget)
    if budget.fencing_token < 0:
        raise ValueError("fencing_token cannot be negative")
    _validate_active_lease(budget)
    terminal_outcome = budget.terminal_outcome
    terminal_result_id = budget.terminal_result_id
    if terminal_outcome is None and terminal_result_id is not None:
        raise ValueError("terminal_result_id requires terminal_outcome")
    if terminal_outcome is not None and budget.active_lease is None:
        raise ValueError("terminal state requires its completing lease")
