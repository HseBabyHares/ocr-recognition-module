"""Birth-date and birth-place extraction rules."""

from __future__ import annotations

from collections.abc import Iterable

from sird_recognition._snils_dates import date_values, remove_date_prefix
from sird_recognition._snils_label_loader import load_ocr_labels
from sird_recognition._snils_labels import OcrLabels, has_label
from sird_recognition._snils_text import birth_place_labels, label_attachment


def _line_candidates(
    lines: list[str], line_index: int, labels: OcrLabels
) -> list[str]:
    candidates = [lines[line_index]]
    next_index = line_index + 1
    if next_index < len(lines):
        following_line = lines[next_index]
        if not has_label(
            following_line, labels.registration_labels
        ) or has_label(following_line, labels.birth_labels):
            candidates.append(following_line)
    return candidates


def _line_birth_values(lines: list[str], labels: OcrLabels) -> set[str]:
    birth_values: set[str] = set()
    for line_index, line in enumerate(lines):
        if not has_label(line, labels.birth_labels):
            continue
        for candidate in _line_candidates(lines, line_index, labels):
            birth_values.update(date_values(candidate, labels.months_genitive))
    return birth_values


def birth_date_candidates(texts: Iterable[str]) -> set[str]:
    """Extract dates from lines labelled as a birth date."""
    labels = load_ocr_labels()
    if labels is None:
        return set()
    return {
        date_value
        for text in texts
        for date_value in _line_birth_values(
            text.splitlines() or [text], labels
        )
    }


def _place_value(
    line: str, place_labels: tuple[str, ...], months: dict[str, int]
) -> str | None:
    attached = label_attachment(line, place_labels)
    if attached is None:
        return None
    stripped = attached.lstrip(" \t:;,.-")
    without_date = remove_date_prefix(stripped, months).strip(" \t:;,.-")
    if not without_date:
        return None
    return " ".join(without_date.split())


def _place_values(texts: Iterable[str], labels: OcrLabels) -> set[str]:
    place_labels = birth_place_labels(labels.birth_labels)
    if not place_labels:
        return set()
    place_values: set[str] = set()
    for text in texts:
        for line in text.splitlines():
            place_value = _place_value(
                line, place_labels, labels.months_genitive
            )
            if place_value is not None:
                place_values.add(place_value)
    return place_values


def optional_unique_birth_place(texts: Iterable[str]) -> str | None:
    """Extract a unique labelled birth place, when present."""
    labels = load_ocr_labels()
    if labels is None:
        return None
    place_values = _place_values(texts, labels)
    return next(iter(place_values)) if len(place_values) == 1 else None
