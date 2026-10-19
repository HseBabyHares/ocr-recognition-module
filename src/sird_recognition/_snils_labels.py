"""Compiled patterns and validated OCR label data structures."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass


class Patterns:
    """Compiled OCR patterns kept together with their limits."""

    numeric_date = re.compile(
        r"(?<!\d)(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})(?!\d)"
    )
    text_date = re.compile(
        r"(?<!\d)(\d{1,2})\s+([^\W\d_]+)\s+(\d{4})(?!\d)",
        re.UNICODE,
    )
    name_token_min = 2
    name_token_max = 30
    name_token_count = 3
    following_line_limit = 3
    following_token_count = 1
    combined_token_min = 2
    short_prefix_max = 2
    combined_token_max = 4
    word = re.compile(r"[^\W\d_]+", re.UNICODE)
    parenthetical = re.compile(r"\([^)]*\)")
    dotted_name_label = re.compile(r"\bф\s*\.\s*и\s*\.\s*о\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class OcrLabels:
    """Validated labels loaded from the packaged OCR resource."""

    birth_labels: tuple[str, ...]
    registration_labels: tuple[str, ...]
    name_label_tokens: frozenset[str]
    months_genitive: dict[str, int]


def normalized_line(raw_line: str) -> str:
    """Normalize spacing and case for label checks."""
    return " ".join(raw_line.casefold().split())


def has_label(line: str, labels: Iterable[str]) -> bool:
    """Return whether one normalized label occurs in a line."""
    normalized = normalized_line(line)
    return any(label in normalized for label in labels)


def word_tokens(line: str) -> list[str]:
    """Return the name-sized words of one OCR line."""
    # "Ф.И.О." splits into one-letter words; "(при наличии)" is no value.
    line = Patterns.dotted_name_label.sub(
        "ФИО", Patterns.parenthetical.sub(" ", line)
    )
    return [
        match.group()
        for match in Patterns.word.finditer(line)
        if (
            Patterns.name_token_min
            <= len(match.group())
            <= Patterns.name_token_max
        )
    ]


_Patterns = Patterns
