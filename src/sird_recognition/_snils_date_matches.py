"""Private helpers for strict OCR date matching."""

from __future__ import annotations

import re
from datetime import date


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
