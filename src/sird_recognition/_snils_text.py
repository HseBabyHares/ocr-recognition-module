"""Label attachment helpers for OCR text."""

from __future__ import annotations

from collections.abc import Iterable

from sird_recognition._snils_labels import _Patterns


def _contains_sequence(
    haystack: tuple[str, ...], needle: tuple[str, ...]
) -> bool:
    if not needle or len(needle) > len(haystack):
        return False
    return any(
        haystack[index : index + len(needle)] == needle
        for index in range(len(haystack) - len(needle) + 1)
    )


def _specific_labels(
    tokenized: dict[str, tuple[str, ...]],
) -> set[str]:
    specific_labels: set[str] = set()
    for label, words in tokenized.items():
        for other_label, other_words in tokenized.items():
            if label != other_label and _contains_sequence(other_words, words):
                specific_labels.update((label, other_label))
    return specific_labels


def birth_place_labels(labels: tuple[str, ...]) -> tuple[str, ...]:
    """Find labels whose words are contained by a more specific label."""
    tokenized = {
        label: tuple(
            token.casefold() for token in _Patterns.word.findall(label)
        )
        for label in labels
    }
    place_labels = _specific_labels(tokenized)
    return tuple(sorted(place_labels, key=len, reverse=True))


def label_attachment(line: str, labels: Iterable[str]) -> str | None:
    """Return the text following the longest matching label."""
    folded = line.casefold()
    for label in sorted(labels, key=len, reverse=True):
        position = folded.find(label)
        if position >= 0:
            return line[position + len(label) :]
    return None
