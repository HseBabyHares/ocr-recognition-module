"""Birth-date and birth-place extraction rules."""

from __future__ import annotations

from collections.abc import Iterable

from sird_recognition._snils_dates import DateReader, date_values
from sird_recognition._snils_label_loader import load_ocr_labels
from sird_recognition._snils_labels import (
    OcrLabels,
    _Patterns,
    has_label,
    normalized_line,
)
from sird_recognition._snils_text import (
    birth_place_labels,
    label_attachment,
    label_end,
)


def _line_candidates(
    lines: list[str], line_index: int, labels: OcrLabels
) -> list[str]:
    candidates = [lines[line_index]]
    next_index = line_index + 1
    if next_index < len(lines):
        following_line = lines[next_index]
        if (
            not has_label(following_line, labels.registration_labels)
            or label_end(following_line, labels.birth_labels) is not None
        ):
            candidates.append(following_line)
    return candidates


def _line_birth_values(
    lines: list[str], labels: OcrLabels, read: DateReader
) -> set[str]:
    birth_values: set[str] = set()
    for line_index, line in enumerate(lines):
        if label_end(line, labels.birth_labels) is None:
            continue
        for candidate in _line_candidates(lines, line_index, labels):
            birth_values.update(read(candidate, labels.months_genitive))
    return birth_values


def birth_date_candidates(
    texts: Iterable[str], read: DateReader = date_values
) -> set[str]:
    """Extract dates from lines labelled as a birth date."""
    labels = load_ocr_labels()
    if labels is None:
        return set()
    return {
        date_value
        for text in texts
        for date_value in _line_birth_values(
            text.splitlines() or [text], labels, read
        )
    }


def _same_line_place(attached: str) -> str:
    # Text up to the year is the date, also when OCR damaged the month.
    date_end = max(
        (year.end() for year in _Patterns.year.finditer(attached)), default=0
    )
    place_text = attached[date_end:].strip()
    # After the date a comma starts the place; without it the first word
    # is "года" or its OCR damage, such as "Ода".
    if date_end and not place_text.startswith(","):
        place_text = "".join(place_text.split(maxsplit=1)[1:])
    return place_text.strip(" \t:;,.-")


def _place_value(
    lines: list[str],
    line_index: int,
    place_labels: tuple[str, ...],
    labels: OcrLabels,
) -> set[str]:
    attached = label_attachment(lines[line_index], place_labels)
    if attached is None:
        return set()
    place_texts = [_same_line_place(attached)]
    # shortcut: only one following line is read, so a two-line place
    # loses its region line; read more lines when such forms arrive.
    for following_line in lines[line_index + 1 : line_index + 2]:
        if not has_label(
            following_line, labels.birth_labels + labels.registration_labels
        ) and normalized_line(following_line).split()[:1] != [
            _Patterns.sex_label
        ]:
            place_texts.append(following_line.strip())
    # OCR noise fails the place shape and is dropped, not counted.
    shaped = [
        " ".join(place_text.split())
        for place_text in place_texts
        if _Patterns.place.fullmatch(place_text)
    ]
    return set(shaped[:1])


def _place_values(texts: Iterable[str], labels: OcrLabels) -> set[str]:
    place_labels = birth_place_labels(labels.birth_labels)
    if not place_labels:
        return set()
    place_values: set[str] = set()
    for text in texts:
        lines = text.splitlines()
        for line_index, _ in enumerate(lines):
            place_values |= _place_value(
                lines, line_index, place_labels, labels
            )
    return place_values


def optional_unique_birth_place(texts: Iterable[str]) -> str | None:
    """Extract a unique labelled birth place, when present."""
    labels = load_ocr_labels()
    if labels is None:
        return None
    place_values = _place_values(texts, labels)
    return next(iter(place_values)) if len(place_values) == 1 else None
