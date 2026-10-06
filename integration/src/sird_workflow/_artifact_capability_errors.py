"""Capability validation error types."""

from sird_workflow.exceptions import WorkflowError


class ArtifactSecurityError(WorkflowError):
    """Base class for artifact capability and decoder-input failures."""


class MalformedCapabilityError(ArtifactSecurityError):
    """The capability envelope or claims are malformed."""


class CapabilitySignatureError(ArtifactSecurityError):
    """The capability MAC is invalid or its key is unavailable."""


class CapabilityClaimMismatchError(ArtifactSecurityError):
    """A capability claim does not match the expected request or artifact."""


class CapabilityExpiredError(ArtifactSecurityError):
    """The capability expiry has passed."""
