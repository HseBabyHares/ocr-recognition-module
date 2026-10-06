"""Artifact source and decoder error types."""

from sird_workflow._artifact_capability_errors import ArtifactSecurityError


class ArtifactReadError(ArtifactSecurityError):
    """The artifact source did not return safe decoder input."""


class ArtifactPolicyError(ArtifactReadError):
    """The artifact violates the configured read policy."""


class ArtifactSizeMismatchError(ArtifactReadError):
    """The source byte count does not match the signed size claim."""


class ArtifactChecksumError(ArtifactReadError):
    """The source bytes do not match the signed SHA-256 checksum."""


class ArtifactDecodeError(ArtifactReadError):
    """The decoder failed after all artifact guards passed."""
