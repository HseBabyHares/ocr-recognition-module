"""Validation error for unsupported or divergent task events."""


class InvalidTaskEventError(ValueError):
    """The payload is not a supported versioned task event."""
