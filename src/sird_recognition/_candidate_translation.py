"""Private translation of model records into candidate spans."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from sird_recognition._candidate_model import field_name
from sird_recognition._candidate_translation_validation import (
    _coordinates,
    _region,
    _score_scale,
)
from sird_recognition.candidate_contracts import CandidateField, CandidateSpan
from sird_recognition.contracts.text_observation import TextObservation

_START_INDEX = 0
_END_INDEX = 1
_SCORE_INDEX = 2


@dataclass(frozen=True, slots=True)
class TranslationSource:
    """Immutable provenance used while translating model records."""

    score_scale: str
    model_id: str
    model_revision: str


def _translation_values(
    candidate_record: object,
    text: str,
) -> tuple[CandidateField, tuple[int, int, float], str] | None:
    if not isinstance(candidate_record, Mapping):
        return None
    typed_record = cast(Mapping[str, Any], candidate_record)
    label = typed_record.get("label")
    candidate_field = field_name(label) if isinstance(label, str) else None
    if candidate_field is None:
        return None
    coordinates = _coordinates(typed_record, text)
    if coordinates is None:
        return None
    raw_text = text[coordinates[_START_INDEX] : coordinates[_END_INDEX]]
    if not raw_text:
        return None
    return CandidateField(candidate_field), coordinates, raw_text


def translate_candidate(
    candidate_record: object,
    text: str,
    observation: TextObservation,
    observation_id: str,
    source: TranslationSource,
) -> CandidateSpan | None:
    """Translate one model record while preserving source provenance."""
    translated = _translation_values(candidate_record, text)
    if translated is None:
        return None
    candidate_field, coordinates, raw_text = translated
    return CandidateSpan(
        field=candidate_field,
        raw_text=raw_text,
        start=coordinates[_START_INDEX],
        end=coordinates[_END_INDEX],
        score=coordinates[_SCORE_INDEX],
        score_scale=_score_scale(
            cast(Mapping[str, Any], candidate_record),
            source.score_scale,
        ),
        observation_id=observation_id,
        model_id=source.model_id,
        model_revision=source.model_revision,
        region=_region(
            cast(Mapping[str, Any], candidate_record),
            observation,
        ),
    )
