"""Rule and model-backed field candidate extraction."""

from __future__ import annotations

from collections.abc import Iterable

from sird_recognition._snils_birth_fields import (
    birth_date_candidates as _birth_date_candidates,
)
from sird_recognition._snils_birth_fields import (
    optional_unique_birth_place as _optional_unique_birth_place,
)
from sird_recognition._snils_dates import DateReader, date_values
from sird_recognition._snils_label_loader import load_ocr_labels
from sird_recognition._snils_labels import _Patterns
from sird_recognition.candidate_contracts import CandidateField, CandidateSpan


def candidate_labels() -> dict[str, Iterable[str]]:
    """Return labels used by the optional candidate extractor."""
    labels = load_ocr_labels()
    if labels is None:
        return {}
    return {
        CandidateField.FULL_NAME: labels.name_label_tokens,
        CandidateField.BIRTH_DATE: labels.birth_labels,
        CandidateField.BIRTH_PLACE: labels.birth_labels,
        CandidateField.REGISTRATION_DATE: labels.registration_labels,
    }


def birth_date_candidates(
    texts: Iterable[str], read: DateReader = date_values
) -> set[str]:
    """Return labelled birth-date candidates."""
    return _birth_date_candidates(texts, read)


def optional_unique_birth_place(texts: Iterable[str]) -> str | None:
    """Return a unique labelled birth place."""
    return _optional_unique_birth_place(texts)


def canonical_place(place_text: str) -> str:
    """Normalize a place while dropping a short region prefix."""
    tokens = place_text.casefold().strip(" ,.;:").split()
    if (
        len(tokens) > 1
        and len(tokens[0].strip(".,;:")) <= _Patterns.short_prefix_max
    ):
        tokens = tokens[1:]
    return " ".join(tokens)


def candidate_values(
    candidates: Iterable[CandidateSpan], field: CandidateField
) -> set[str]:
    """Return non-empty candidate text for one field."""
    return {
        " ".join(candidate.raw_text.split())
        for candidate in candidates
        if candidate.field is field and candidate.raw_text.strip()
    }


def candidate_birth_dates(
    candidates: Iterable[CandidateSpan], read: DateReader = date_values
) -> set[str]:
    """Extract valid birth dates from model candidates."""
    labels = load_ocr_labels()
    if labels is None:
        return set()
    return {
        date_candidate
        for candidate in candidates
        if candidate.field is CandidateField.BIRTH_DATE
        for date_candidate in read(candidate.raw_text, labels.months_genitive)
    }
