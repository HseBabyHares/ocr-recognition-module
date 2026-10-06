"""Private definition module for public SPIFFE policy exceptions."""


class SpiffePolicyError(ValueError):
    """Base error for invalid or unauthorized workload policy inputs."""


class MalformedSpiffeIdError(SpiffePolicyError):
    """Raised when an identity is not a valid SPIFFE ID."""


class EmptyAuthorizationPolicyError(SpiffePolicyError):
    """Raised when an authorization policy has no allowed identities."""


class UnknownWorkloadRoleError(SpiffePolicyError):
    """Raised when a role value is not a valid configured role."""


class InvalidCredentialError(SpiffePolicyError):
    """Raised when credential metadata is invalid or inconsistent."""


class ExpiredCredentialError(InvalidCredentialError):
    """Raised when credential metadata is expired at validation time."""


class UnauthorizedWorkloadError(SpiffePolicyError):
    """Raised when an identity is not allowed to use a requested role."""
