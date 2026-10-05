"""OCR observation flow after image variants are prepared."""

from __future__ import annotations

from dataclasses import dataclass

from sird_recognition._snils_checks import is_valid_snils, snils_candidates
from sird_recognition._snils_compat import refused_result
from sird_recognition._snils_field_resolution import (
    VerifiedInputs,
    assemble_verified_result,
)
from sird_recognition._snils_observations import (
    ObservationInputs,
    bind_observation_candidates,
    read_observations,
)
from sird_recognition._snils_types import (
    SnilsRecognitionResult,
    SnilsTextReader,
)
from sird_recognition.candidate_extraction import CandidateExtractor
from sird_recognition.contracts.text_observation import TextObservation


@dataclass(frozen=True, slots=True)
class RecognitionInputs:
    """Bound OCR inputs passed between flow stages."""

    reader: SnilsTextReader
    candidate_extractor: CandidateExtractor | None
    variants: tuple[bytes, ...]
    timeout_seconds: float
    language: str
    cpu_threads: int


def recognize_variants(inputs: RecognitionInputs) -> SnilsRecognitionResult:
    """Read variants in order and reconcile their evidence."""
    observations, diagnostics = read_observations(
        ObservationInputs(
            inputs.reader,
            inputs.variants,
            inputs.timeout_seconds,
            inputs.language,
            inputs.cpu_threads,
        )
    )
    if not observations:
        diagnostics.append("unreadable")
        return refused_result(
            tuple(dict.fromkeys(diagnostics)), len(inputs.variants), 0
        )
    return _recognize_observations(observations, diagnostics, inputs)


def _recognize_observations(
    observations: list[TextObservation],
    diagnostics: list[str],
    inputs: RecognitionInputs,
) -> SnilsRecognitionResult:
    texts = tuple(observation.raw_text for observation in observations)
    candidates = snils_candidates(texts)
    valid = tuple(
        candidate for candidate in candidates if is_valid_snils(candidate)
    )
    if not valid:
        return refused_result(
            tuple(dict.fromkeys((*diagnostics, "snils_missing_or_invalid"))),
            len(inputs.variants),
            len(observations),
        )
    if len(set(valid)) != 1:
        return refused_result(
            tuple(dict.fromkeys((*diagnostics, "snils_ambiguous"))),
            len(inputs.variants),
            len(observations),
        )
    bound_candidates, binding_diagnostics = bind_observation_candidates(
        inputs.candidate_extractor, observations
    )
    diagnostics.extend(binding_diagnostics)
    return assemble_verified_result(
        VerifiedInputs(
            valid[0],
            texts,
            diagnostics,
            len(inputs.variants),
            len(observations),
            tuple(bound_candidates),
        )
    )
