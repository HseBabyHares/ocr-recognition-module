"""Label and region binding for candidate spans."""

from collections.abc import Iterable, Mapping

from sird_recognition._candidate_binding_match import (
    BindingContext,
    is_bound,
)
from sird_recognition._candidate_binding_names import name_run_ids
from sird_recognition.candidate_contracts import CandidateField, CandidateSpan
from sird_recognition.contracts.text_observation import TextObservation


def _normalize_labels[LabelKey: str](
    labels: Mapping[LabelKey, Iterable[str]],
) -> dict[CandidateField, tuple[str, ...]]:
    normalized_labels: dict[CandidateField, tuple[str, ...]] = {}
    for key, label_values in labels.items():
        if not isinstance(key, str):
            continue
        normalized_labels[CandidateField(key)] = tuple(
            " ".join(label.casefold().split())
            for label in label_values
            if isinstance(label, str) and label.strip()
        )
    return normalized_labels


def _line_offsets(lines: list[str]) -> list[tuple[int, int]]:
    offsets: list[tuple[int, int]] = []
    cursor = 0
    for line in lines:
        offsets.append((cursor, cursor + len(line)))
        cursor += len(line) + 1
    return offsets


def bind_candidates[LabelKey: str](
    observation: TextObservation,
    candidates: Iterable[CandidateSpan],
    labels: Mapping[LabelKey, Iterable[str]],
) -> tuple[CandidateSpan, ...]:
    """Keep candidates with an explicit label or region binding."""
    if not isinstance(observation, TextObservation):
        raise TypeError("observation must be a TextObservation")
    candidate_values = tuple(candidates)
    lines = observation.raw_text.splitlines()
    binding_context: BindingContext = (
        lines,
        _line_offsets(lines),
        _normalize_labels(labels),
    )
    name_candidates = name_run_ids(observation, candidate_values)
    return tuple(
        candidate
        for candidate in candidate_values
        if is_bound(
            candidate,
            candidate_values,
            name_candidates,
            binding_context,
        )
    )


bind_candidates.__module__ = "sird_recognition.candidate_extraction"
