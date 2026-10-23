"""Reconcile field evidence into verified SNILS results."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sird_recognition._snils_dates import text_date_values
from sird_recognition._snils_field_candidates import (
    birth_date_candidates,
    candidate_birth_dates,
    candidate_values,
    optional_unique_birth_place,
)
from sird_recognition._snils_labels import _Patterns
from sird_recognition._snils_name_resolution import resolve_name
from sird_recognition._snils_types import (
    SnilsRecognitionResult,
    SnilsRecognitionStatus,
)
from sird_recognition.candidate_extraction import CandidateField, CandidateSpan


@dataclass(frozen=True, slots=True)
class VerifiedInputs:
    """Evidence required to assemble a verified result."""

    snils: str
    texts: tuple[str, ...]
    diagnostics: Iterable[str]
    variant_count: int
    observation_count: int
    bound_candidates: tuple[CandidateSpan, ...]


def resolve_birth_date(
    texts: tuple[str, ...],
    bound_candidates: tuple[CandidateSpan, ...],
) -> tuple[str | None, set[str]]:
    """Resolve a unique birth date and retain ambiguity evidence."""
    # The card writes the birth date with a month name and the registration
    # date with digits, so a month-name date excludes every numeric date.
    candidates = birth_date_candidates(texts, text_date_values)
    candidates.update(
        candidate_birth_dates(bound_candidates, text_date_values)
    )
    if not candidates:
        candidates = birth_date_candidates(texts)
        candidates.update(candidate_birth_dates(bound_candidates))
    birth_date = next(iter(candidates)) if len(candidates) == 1 else None
    return birth_date, candidates


def _canonical_place(place_text: str) -> str:
    tokens = place_text.casefold().strip(" ,.;:").split()
    if (
        len(tokens) > 1
        and len(tokens[0].strip(".,;:")) <= _Patterns.short_prefix_max
    ):
        tokens = tokens[1:]
    return " ".join(tokens)


def _optional_canonical_place(place_text: str | None) -> str | None:
    if place_text is None:
        return None
    return _canonical_place(place_text)


def resolve_birth_place(
    texts: tuple[str, ...],
    bound_candidates: tuple[CandidateSpan, ...],
) -> str | None:
    """Reconcile optional rule and model birth-place evidence."""
    birth_place = optional_unique_birth_place(texts)
    model_places = candidate_values(
        bound_candidates, CandidateField.BIRTH_PLACE
    )
    if not model_places:
        return birth_place
    rule_place = _optional_canonical_place(birth_place)
    model_canonical = {
        _canonical_place(model_place) for model_place in model_places
    }
    if rule_place is not None:
        return birth_place if model_canonical == {rule_place} else None
    if len(model_canonical) == 1:
        return next(iter(model_places))
    return birth_place


def _verified_diagnostics(
    inputs: VerifiedInputs,
    name: str | None,
    name_evidence: set[str],
    birth_date: str | None,
    date_evidence: set[str],
) -> tuple[str, ...]:
    result_diagnostics = list(inputs.diagnostics)
    if name is None and len(name_evidence) > 1:
        result_diagnostics.append("name_ambiguous")
    if birth_date is None and len(date_evidence) > 1:
        result_diagnostics.append("birth_date_ambiguous")
    result_diagnostics.append("snils_checksum_valid")
    return tuple(dict.fromkeys(result_diagnostics))


def assemble_verified_result(inputs: VerifiedInputs) -> SnilsRecognitionResult:
    """Construct the verified result and stable diagnostics order."""
    name, name_evidence = resolve_name(inputs.texts, inputs.bound_candidates)
    birth_date, date_evidence = resolve_birth_date(
        inputs.texts, inputs.bound_candidates
    )
    birth_place = resolve_birth_place(inputs.texts, inputs.bound_candidates)
    return SnilsRecognitionResult(
        SnilsRecognitionStatus.VERIFIED,
        inputs.snils,
        name,
        birth_date,
        _verified_diagnostics(
            inputs, name, name_evidence, birth_date, date_evidence
        ),
        inputs.variant_count,
        inputs.observation_count,
        birth_place,
    )
