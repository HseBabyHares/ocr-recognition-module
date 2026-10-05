"""Model name span reconciliation helpers."""

from __future__ import annotations

from collections.abc import Iterable

from sird_recognition._snils_labels import _Patterns
from sird_recognition._snils_name_value_spans import (
    combined_values,
    observation_id,
)
from sird_recognition.candidate_extraction import CandidateField, CandidateSpan


def strict_name_subset(name_value: str, combined: str) -> bool:
    """Return whether name_value is a strict contiguous name subset."""
    value_tokens = tuple(_Patterns.word.findall(name_value.casefold()))
    combined_tokens = tuple(_Patterns.word.findall(combined.casefold()))
    return bool(
        value_tokens
        and len(value_tokens) < len(combined_tokens)
        and any(
            combined_tokens[index : index + len(value_tokens)] == value_tokens
            for index in range(len(combined_tokens) - len(value_tokens) + 1)
        )
    )


def _full_name_candidates(
    candidates: Iterable[CandidateSpan],
) -> tuple[CandidateSpan, ...]:
    return tuple(
        candidate
        for candidate in candidates
        if candidate.field is CandidateField.FULL_NAME
    )


def _candidate_observation_ids(
    observation_ids: Iterable[str] | None,
) -> tuple[str, ...] | None:
    return None if observation_ids is None else tuple(observation_ids)


def _collect_name_values(
    candidates: tuple[CandidateSpan, ...],
    texts: Iterable[str],
    observation_ids: tuple[str, ...] | None,
) -> set[str]:
    name_values: set[str] = set()
    for text_index, text in enumerate(texts):
        current_observation_id = observation_id(observation_ids, text_index)
        name_values.update(
            combined_values(candidates, text, current_observation_id)
        )
    return name_values


def candidate_name_values(
    candidates: Iterable[CandidateSpan],
    texts: Iterable[str],
    observation_ids: Iterable[str] | None = None,
) -> set[str]:
    """Join adjacent model spans into bounded full-name candidates."""
    return _collect_name_values(
        _full_name_candidates(candidates),
        texts,
        _candidate_observation_ids(observation_ids),
    )
