"""Shared fail-closed validation for artifact claims."""

from datetime import UTC, datetime

from sird_workflow._artifact_constants import HEX_BASE, SHA256_HEX_LENGTH


def require_text(candidate: object, field_name: str) -> str:
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return candidate


def normalise_object_id(candidate: object) -> str:
    object_id = require_text(candidate, "object_id")
    if "/" in object_id or "\\" in object_id or "://" in object_id:
        raise ValueError("object_id must be an opaque identifier")
    return object_id


def normalise_checksum(candidate: object) -> str:
    field_name = "checksum"
    error_message = "checksum must be a SHA-256 hexadecimal digest"
    checksum = require_text(candidate, field_name).lower()
    if checksum.startswith("sha256:"):
        checksum = checksum.removeprefix("sha256:")
    if len(checksum) != SHA256_HEX_LENGTH:
        raise ValueError(error_message)
    try:
        int(checksum, HEX_BASE)
    except ValueError as exc:
        raise ValueError(error_message) from exc
    return checksum


def normalise_generation(candidate: object) -> str | int:
    if isinstance(candidate, bool):
        raise ValueError(
            "generation must be a non-empty string or non-negative integer"
        )
    if isinstance(candidate, int):
        if candidate < 0:
            raise ValueError("generation must be non-negative")
        return candidate
    return require_text(candidate, "generation")


def normalise_media_type(candidate: object) -> str:
    return require_text(candidate, "media_type").lower()


def normalise_expiry(candidate: datetime) -> datetime:
    if not isinstance(candidate, datetime) or candidate.tzinfo is None:
        raise ValueError("expires_at must be timezone-aware")
    return candidate.astimezone(UTC)
