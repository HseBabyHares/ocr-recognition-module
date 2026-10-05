"""Private helpers for strict OCR date matching."""

from __future__ import annotations

import re
from datetime import date

from sird_recognition._snils_labels import _Patterns


def numeric_match_date(date_match: re.Match[str]) -> str | None:
    try:
        return date(
            int(date_match.group(3)),
            int(date_match.group(2)),
            int(date_match.group(1)),
        ).isoformat()
    except (TypeError, ValueError):
        return None


def text_match_date(
    date_match: re.Match[str], months: dict[str, int]
) -> str | None:
    month_number = months.get(date_match.group(2).casefold())
    if month_number is None:
        return None
    try:
        return date(
            int(date_match.group(3)),
            int(month_number),
            int(date_match.group(1)),
        ).isoformat()
    except (TypeError, ValueError):
        return None


def numeric_prefix(raw_text: str) -> str | None:
    for date_match in _Patterns.numeric_date.finditer(raw_text):
        if date_match.start() != 0:
            break
        if numeric_match_date(date_match) is not None:
            return raw_text[date_match.end() :]
    return None


def text_prefix(raw_text: str, months: dict[str, int]) -> str | None:
    for date_match in _Patterns.text_date.finditer(raw_text):
        if date_match.start() != 0:
            break
        if text_match_date(date_match, months) is not None:
            return raw_text[date_match.end() :]
    return None
