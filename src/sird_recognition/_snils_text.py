"""Label attachment helpers for OCR text."""

from __future__ import annotations

from collections.abc import Iterable
from difflib import SequenceMatcher

from sird_recognition._snils_labels import _Patterns

_WORD_RATIO = 0.75


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


def _misses(words: list[str], label_words: list[str]) -> int:
    # A ratio of 0.75 allows one OCR error in four letters.
    return sum(
        SequenceMatcher(None, word, label_word).ratio() < _WORD_RATIO
        for word, label_word in zip(words, label_words, strict=True)
    )


def _window_end(folded: str, label: str) -> int | None:
    words = list(_Patterns.word.finditer(folded))
    label_words = _Patterns.word.findall(label)
    # OCR damage can hide one word of a long label, never of a short one.
    allowed_misses = (len(label_words) - 1) // 2
    for start in range(len(words) - len(label_words) + 1):
        window = words[start : start + len(label_words)]
        if (
            _misses([word.group() for word in window], label_words)
            <= allowed_misses
        ):
            return window[-1].end()
    return None


def label_end(line: str, labels: Iterable[str]) -> int | None:
    """Return the end of the longest label, with OCR errors in its words."""
    folded = line.casefold()
    for label in sorted(labels, key=len, reverse=True):
        position = folded.find(label)
        end = (
            position + len(label)
            if position >= 0
            else _window_end(folded, label)
        )
        if end is not None:
            return end
    return None


def label_attachment(line: str, labels: Iterable[str]) -> str | None:
    """Return the text following the longest matching label."""
    end = label_end(line, labels)
    return None if end is None else line[end:]
