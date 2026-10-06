"""Pure attempt-budget and lease-fencing state transitions.

The integration service persists the returned records in its transaction.  This
module does not keep process-local state and does not perform persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final

from sird_workflow import _attempt_validation as validation
from sird_workflow._attempt_errors import (
    AttemptBudgetExhaustedError,
    DuplicateTerminalTransitionError,
    StaleAttemptLeaseError,
)

DEFAULT_MAX_ATTEMPTS: Final = 3


@dataclass(frozen=True, slots=True)
class AttemptLease:
    """A worker's fenced claim for one logical task delivery attempt."""

    task_id: str
    attempt_number: int
    fencing_token: int
    worker_id: str
    lease_id: str
    delivery_id: str

    def __post_init__(self) -> None:
        validation.require_text(self.task_id, "task_id")
        validation.require_text(self.worker_id, "worker_id")
        validation.require_text(self.lease_id, "lease_id")
        validation.require_text(self.delivery_id, "delivery_id")
        if self.attempt_number <= 0:
            raise ValueError("attempt_number must be positive")
        if self.fencing_token <= 0:
            raise ValueError("fencing_token must be positive")


def _resolve_delivery_id(
    budget: AttemptBudget,
    delivery_id: str | None,
) -> str:
    next_attempt = budget.attempts_used + 1
    resolved = delivery_id or f"{budget.task_id}:attempt:{next_attempt}"
    return validation.require_text(resolved, "delivery_id")


def _resume_claim(
    budget: AttemptBudget,
    current: AttemptLease,
    worker_id: str,
    lease_id: str | None,
) -> tuple[AttemptBudget, AttemptLease]:
    next_token = max(budget.fencing_token, current.fencing_token) + 1
    resumed = replace(
        current,
        worker_id=worker_id,
        fencing_token=next_token,
        lease_id=lease_id or current.lease_id,
    )
    return replace(
        budget,
        fencing_token=next_token,
        active_lease=resumed,
    ), resumed


def _new_claim(
    budget: AttemptBudget,
    worker_id: str,
    delivery_id: str,
    lease_id: str | None,
) -> tuple[AttemptBudget, AttemptLease]:
    if budget.is_exhausted:
        raise AttemptBudgetExhaustedError(
            f"task {budget.task_id!r} exhausted its "
            f"{budget.max_attempts}-attempt budget"
        )
    attempt_number = budget.attempts_used + 1
    next_token = max(budget.fencing_token, 0) + 1
    resolved_lease_id = lease_id or f"{budget.task_id}:{delivery_id}"
    lease = AttemptLease(
        task_id=budget.task_id,
        attempt_number=attempt_number,
        fencing_token=next_token,
        worker_id=worker_id,
        lease_id=resolved_lease_id,
        delivery_id=delivery_id,
    )
    next_budget = replace(
        budget,
        attempts_used=attempt_number,
        fencing_token=next_token,
        active_lease=lease,
    )
    return next_budget, lease


@dataclass(frozen=True, slots=True)
class AttemptBudget:
    """Durable-shaped state for one task's shared attempt budget.

    ``claim`` returns a new state and lease.  A redelivery with the same
    ``delivery_id`` resumes the same logical attempt and does not consume a
    second budget unit.  A different worker receives a new fencing token, so a
    lease held by the previous worker becomes stale.
    """

    task_id: str
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    attempts_used: int = 0
    fencing_token: int = 0
    active_lease: AttemptLease | None = None
    terminal_outcome: str | None = None
    terminal_result_id: str | None = None

    def __post_init__(self) -> None:
        validation.validate_budget(self)

    @property
    def is_terminal(self) -> bool:
        return self.terminal_outcome is not None

    @property
    def is_exhausted(self) -> bool:
        return self.attempts_used >= self.max_attempts

    def claim(
        self,
        worker_id: str,
        *,
        delivery_id: str | None = None,
        lease_id: str | None = None,
    ) -> tuple[AttemptBudget, AttemptLease]:
        """Claim a delivery, returning the next state and its fenced lease.

        Replaying the same delivery resumes its existing attempt.  A takeover
        by another worker changes only the fencing token.  A new delivery
        consumes one shared attempt, including redelivery after a released or
        completed non-terminal processing step.
        """

        validation.require_text(worker_id, "worker_id")
        if self.is_terminal:
            raise DuplicateTerminalTransitionError(
                f"task {self.task_id!r} already has terminal outcome"
            )
        resolved_delivery_id = _resolve_delivery_id(self, delivery_id)
        current = self.active_lease
        if current is not None and current.delivery_id == resolved_delivery_id:
            if current.worker_id == worker_id:
                return self, current
            return _resume_claim(self, current, worker_id, lease_id)
        return _new_claim(self, worker_id, resolved_delivery_id, lease_id)

    def release(self, lease: AttemptLease) -> AttemptBudget:
        """Release a current non-terminal lease without refunding its
        attempt."""

        self._require_current_lease(lease)
        if self.is_terminal:
            raise DuplicateTerminalTransitionError(
                f"task {self.task_id!r} already has terminal outcome"
            )
        return replace(self, active_lease=None)

    def complete(
        self,
        lease: AttemptLease,
        *,
        outcome: str,
        result_id: str | None = None,
    ) -> AttemptBudget:
        """Apply the one terminal transition guarded by the current lease."""

        self._require_current_lease(lease)
        if self.is_terminal:
            raise DuplicateTerminalTransitionError(
                f"task {self.task_id!r} already has terminal outcome"
            )
        validation.require_text(outcome, "outcome")
        if result_id is not None:
            validation.require_text(result_id, "result_id")
        return replace(
            self,
            terminal_outcome=outcome,
            terminal_result_id=result_id,
        )

    mark_terminal = complete

    def _require_current_lease(self, lease: AttemptLease) -> None:
        current = self.active_lease
        if current is None or lease != current:
            raise StaleAttemptLeaseError(
                f"lease {lease.lease_id!r} is stale for task {self.task_id!r}"
            )
        if lease.task_id != self.task_id:
            raise StaleAttemptLeaseError(
                "lease task_id does not match budget task_id"
            )
