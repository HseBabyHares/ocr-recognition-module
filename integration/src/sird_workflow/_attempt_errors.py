"""Exceptions raised by attempt-budget transitions."""


class AttemptError(Exception):
    """Base class for attempt-budget transition failures."""


class AttemptBudgetExhaustedError(AttemptError):
    """No unused shared attempt remains for a task."""


class StaleAttemptLeaseError(AttemptError):
    """A worker presented a lease that is no longer fenced as current."""


class DuplicateTerminalTransitionError(AttemptError):
    """A task already has its one terminal transition."""


class InvalidAttemptStateError(AttemptError):
    """A persisted attempt state violates the transition invariants."""
