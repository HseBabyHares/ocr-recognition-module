"""Validation helpers for packaged OCR labels."""

from __future__ import annotations

from typing import cast

_MONTH_MIN = 1
_MONTH_MAX = 12


def string_tuple(entries: object) -> tuple[str, ...] | None:
    """Normalize a non-empty list of label strings."""
    if not isinstance(entries, list) or not entries:
        return None
    normalized: list[str] = []
    for entry in entries:
        if not isinstance(entry, str) or not entry.strip():
            return None
        normalized.append(" ".join(entry.casefold().split()))
    return tuple(normalized)


def _valid_month(label: object, month_number: object) -> bool:
    if not isinstance(label, str) or not label.strip():
        return False
    return (
        isinstance(month_number, int)
        and not isinstance(month_number, bool)
        and _MONTH_MIN <= month_number <= _MONTH_MAX
    )


def month_values(entries: object) -> dict[str, int] | None:
    """Validate the genitive month mapping."""
    if not isinstance(entries, dict):
        return None
    months: dict[str, int] = {}
    for label, month_number in entries.items():
        if not _valid_month(label, month_number):
            return None
        months[cast(str, label).casefold()] = cast(int, month_number)
    return months or None
