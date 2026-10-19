"""Strict date extraction from OCR text."""

from __future__ import annotations

from datetime import date

from sird_recognition._snils_date_matches import (
    numeric_match_date,
    text_match_date,
)
from sird_recognition._snils_labels import _Patterns


def parsed_date(day: str, month: int | str, year: str) -> str | None:
    """Return an ISO date only when the calendar date is valid."""
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except (TypeError, ValueError):
        return None


def numeric_date_values(text: str) -> set[str]:
    """Extract valid numeric dates."""
    date_values_found: set[str] = set()
    for date_match in _Patterns.numeric_date.finditer(text):
        parsed_value = numeric_match_date(date_match)
        if parsed_value is not None:
            date_values_found.add(parsed_value)
    return date_values_found


def text_date_values(text: str, months: dict[str, int]) -> set[str]:
    """Extract valid genitive-month dates."""
    date_values_found: set[str] = set()
    for date_match in _Patterns.text_date.finditer(text):
        parsed_value = text_match_date(date_match, months)
        if parsed_value is not None:
            date_values_found.add(parsed_value)
    return date_values_found


def date_values(text: str, months: dict[str, int]) -> set[str]:
    """Extract both supported date spellings."""
    return numeric_date_values(text) | text_date_values(text, months)
