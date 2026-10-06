"""Enumerations used by the corpus manifest model."""

from __future__ import annotations

from enum import StrEnum


class FieldPresence(StrEnum):
    """Whether a field is present in the physical document."""

    PRESENT = "true"
    ABSENT = "false"
    UNKNOWN = "unknown"


class FieldReadability(StrEnum):
    """Visibility quality of a field area."""

    READABLE = "readable"
    UNREADABLE = "unreadable"
    DISPUTED = "disputed"


class CorpusEvidenceStatus(StrEnum):
    """Terminal status of corpus validation."""

    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    ERROR = "error"


CorpusStatus = CorpusEvidenceStatus


def presence(field_presence: FieldPresence | bool | str) -> FieldPresence:
    """Normalize a field-presence value."""
    if isinstance(field_presence, bool):
        return (
            FieldPresence.PRESENT if field_presence else FieldPresence.ABSENT
        )
    return FieldPresence(field_presence)


def readability(field_readability: FieldReadability | str) -> FieldReadability:
    """Normalize a field-readability value."""
    return FieldReadability(field_readability)
