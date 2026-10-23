"""Rule-based full-name extraction from OCR lines."""

from __future__ import annotations

from collections.abc import Iterable

from sird_recognition._snils_label_loader import load_ocr_labels
from sird_recognition._snils_labels import (
    _Patterns,
    has_label,
    word_tokens,
)

_NAME_PARTS = ("фамилия", "имя", "отчество")
# Printed card words form three-word runs that look like a name.
_HEADER_WORDS = frozenset(
    (
        "российская",
        "федерация",
        "страховое",
        "свидетельство",
        "государственного",
        "пенсионного",
        "страхования",
        "пенсионный",
        "фонд",
        "дата",
        "место",
        "рождения",
        "регистрации",
        "пол",
        "мужской",
        "женский",
    )
)


def _last_name_marker(tokens: list[str], name_label_tokens: frozenset[str]):
    marker_indexes = [
        token_index
        for token_index, token in enumerate(tokens)
        if token.casefold() in name_label_tokens
    ]
    return marker_indexes[-1] if marker_indexes else None


def _following_name_tokens(
    lines: list[str],
    line_index: int,
    name_tokens: list[str],
    field_labels: tuple[str, ...],
) -> list[str]:
    for following_line in lines[
        line_index + 1 : line_index + _Patterns.following_line_limit
    ]:
        if has_label(following_line, field_labels):
            break
        following_tokens = word_tokens(following_line)
        if len(following_tokens) != _Patterns.following_token_count:
            break
        name_tokens.extend(following_tokens)
    return name_tokens


def _labelled_name(
    lines: list[str],
    line_index: int,
    tokens: list[str],
    name_label_tokens: frozenset[str],
    field_labels: tuple[str, ...],
) -> list[str] | None:
    marker_index = _last_name_marker(tokens, name_label_tokens)
    if marker_index is None:
        return None
    name_tokens = [
        token
        for token in tokens[marker_index + 1 :]
        if token.casefold() not in name_label_tokens
    ]
    return _following_name_tokens(
        lines,
        line_index,
        name_tokens,
        field_labels,
    )


def _unlabelled_values(
    tokens: list[str], name_label_tokens: frozenset[str]
) -> set[str]:
    return {
        " ".join(candidate_tokens)
        for token_index, _ in enumerate(
            tokens[: len(tokens) - _Patterns.name_token_count + 1]
        )
        for candidate_tokens in (
            tokens[token_index : token_index + _Patterns.name_token_count],
        )
        if not any(
            token.casefold() in name_label_tokens | _HEADER_WORDS
            for token in candidate_tokens
        )
    }


def _line_name_values(
    lines: list[str],
    name_label_tokens: frozenset[str],
    field_labels: tuple[str, ...],
) -> set[tuple[bool, str]]:
    name_values = {(True, name) for name in _field_labelled_names(lines)}
    for line_index, line in enumerate(lines):
        if has_label(line, field_labels):
            continue
        tokens = word_tokens(line)
        labelled_name = _labelled_name(
            lines,
            line_index,
            tokens,
            name_label_tokens,
            field_labels,
        )
        if labelled_name is not None:
            if len(labelled_name) == _Patterns.name_token_count:
                name_values.add((True, " ".join(labelled_name)))
            continue
        name_values.update(
            (False, name_value)
            for name_value in _unlabelled_values(tokens, name_label_tokens)
        )
    return name_values


def _field_labelled_names(lines: list[str]) -> set[str]:
    """Join one-word values of separate surname, name and patronymic rows."""
    rows = [tokens for tokens in map(word_tokens, lines) if tokens]
    found = [
        [tokens[1:] for tokens in rows if tokens[0].casefold() == part]
        for part in _NAME_PARTS
    ]
    *named, patronymic = [
        [len(tail) for tail in part_rows] for part_rows in found
    ]
    # A person without a patronymic leaves that row empty.
    if patronymic not in ([0], [1]):
        return set()
    if any(shape != [1] for shape in named):
        return set()
    return {" ".join(word for part_rows in found for word in part_rows[0])}


def name_candidates(texts: Iterable[str]) -> set[str]:
    """Extract full names from labelled or unlabelled OCR lines."""
    labels = load_ocr_labels()
    if labels is None:
        return set()
    field_labels = labels.birth_labels + labels.registration_labels
    found = {
        name_value
        for text in texts
        for name_value in _line_name_values(
            text.splitlines(), labels.name_label_tokens, field_labels
        )
    }
    # A labelled name outranks word runs from headers and stamps.
    return {name for is_labelled, name in found if is_labelled} or {
        name for _, name in found
    }
