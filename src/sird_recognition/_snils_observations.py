"""Bounded OCR observation and optional candidate-model orchestration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

from sird_recognition._snils_field_candidates import candidate_labels
from sird_recognition._snils_types import SnilsTextReader
from sird_recognition.candidate_extraction import (
    CandidateExtractor,
    CandidateSpan,
    bind_candidates,
)
from sird_recognition.contracts.text_observation import TextObservation


@dataclass(frozen=True, slots=True)
class ObservationInputs:
    """Bound parameters for one ordered OCR variant pass."""

    reader: SnilsTextReader
    variants: tuple[bytes, ...]
    timeout_seconds: float
    language: str
    cpu_threads: int


def read_observations(
    inputs: ObservationInputs,
) -> tuple[list[TextObservation], list[str]]:
    """Read variants in order while preserving per-variant diagnostics."""
    observations: list[TextObservation] = []
    diagnostics: list[str] = []
    for variant in inputs.variants:
        try:
            observation = inputs.reader.read(
                variant,
                timeout_seconds=inputs.timeout_seconds,
                language=inputs.language,
                cpu_threads=inputs.cpu_threads,
            )
        except Exception:
            diagnostics.append("reader_error")
            continue
        if isinstance(observation, TextObservation):
            observations.append(observation)
        else:
            diagnostics.append("reader_error")
    return observations, diagnostics


def _bind_observation_candidates(
    observation: TextObservation,
    extracted: tuple[CandidateSpan, ...],
    labels: dict[str, Iterable[str]],
    observation_index: int,
) -> tuple[CandidateSpan, ...]:
    observation_id = f"observation-{observation_index}"
    return tuple(
        replace(candidate, observation_id=observation_id)
        for candidate in bind_candidates(observation, extracted, labels)
    )


def _extract_bound_candidates(
    extractor: CandidateExtractor,
    observation: TextObservation,
    labels: dict[str, Iterable[str]],
    observation_index: int,
) -> tuple[CandidateSpan, ...]:
    extracted = extractor.extract(observation)
    return _bind_observation_candidates(
        observation, extracted, labels, observation_index
    )


def bind_observation_candidates(
    extractor: CandidateExtractor | None,
    observations: list[TextObservation],
) -> tuple[list[CandidateSpan], list[str]]:
    """Bind extracted spans to observations without affecting OCR flow."""
    if extractor is None:
        return [], []
    labels = candidate_labels()
    bound_candidates: list[CandidateSpan] = []
    diagnostics: list[str] = []
    for observation_index, observation in enumerate(observations):
        try:
            bound_candidates.extend(
                _extract_bound_candidates(
                    extractor, observation, labels, observation_index
                )
            )
        except Exception:
            diagnostics.append("candidate_extractor_unavailable")
    return bound_candidates, diagnostics
