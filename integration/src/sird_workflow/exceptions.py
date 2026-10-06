"""Explicit failures exposed by the workflow service."""


class WorkflowError(Exception):
    """Base class for workflow failures."""


class UnauthenticatedCallerError(WorkflowError):
    """The caller identity is not an allowed SIRD backend identity."""


class InvalidIdempotentReuseError(WorkflowError):
    """An existing task identity was reused with different request content."""


class TaskNotFoundError(WorkflowError):
    """The requested task does not exist."""


class PublicationFailureError(WorkflowError):
    """The task event did not receive a RabbitMQ broker confirmation."""
