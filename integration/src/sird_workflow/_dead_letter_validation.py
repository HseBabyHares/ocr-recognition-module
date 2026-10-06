"""Validation helpers for dead-letter values."""


def require_text(candidate: str, field_name: str) -> str:
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return candidate
