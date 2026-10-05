"""Private span operations for model name reconciliation."""

from __future__ import annotations

from sird_recognition._snils_name_value_candidates import (
    valid_span,
    values_from_start,
)
from sird_recognition.candidate_extraction import CandidateSpan


def observation_id(
    observation_ids: tuple[str, ...] | None, index: int
) -> str | None:
    """Return the observation id at one text index, when supplied."""
    if observation_ids is None:
        return None
    return observation_ids[index]


def matching_spans(
    candidates: tuple[CandidateSpan, ...],
    text: str,
    observation_id: str | None,
) -> list[CandidateSpan]:
    """Return model spans that exactly match one observation text."""
    spans = [
        candidate
        for candidate in candidates
        if (
            observation_id is None
            or candidate.observation_id == observation_id
        )
        and valid_span(candidate, text)
    ]
    return sorted(
        spans, key=lambda candidate: (candidate.start, candidate.end)
    )


def combined_values(
    candidates: tuple[CandidateSpan, ...],
    text: str,
    observation_id: str | None,
) -> set[str]:
    """Build maximal contiguous model name candidates for one text."""
    spans = matching_spans(candidates, text, observation_id)
    name_values: set[str] = set()
    for first_index, _ in enumerate(spans):
        name_values.update(values_from_start(text, spans, first_index))
    return name_values
