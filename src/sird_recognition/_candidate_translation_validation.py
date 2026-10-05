"""Validation helpers for model candidate translation."""

from collections.abc import Mapping
from typing import Any, cast

from sird_recognition.contracts.text_observation import (
    TextObservation,
    TextRegion,
)

_START_INDEX = 0
_END_INDEX = 1
_ZERO_SCORE = float(0)


def _raw_coordinates(
    typed_record: Mapping[str, Any],
) -> tuple[object, object, object]:
    return (
        typed_record["start"],
        typed_record["end"],
        typed_record.get("score", typed_record.get("raw_score", _ZERO_SCORE)),
    )


def _valid_offsets(start: object, end: object, text: str) -> bool:
    if isinstance(start, bool) or not isinstance(start, int):
        return False
    if isinstance(end, bool) or not isinstance(end, int):
        return False
    if start < _START_INDEX or end < start:
        return False
    return end <= len(text)


def _valid_coordinates(
    coordinate_values: tuple[object, object, object],
    text: str,
) -> tuple[int, int, float] | None:
    start, end, score = coordinate_values
    if not _valid_offsets(start, end, text):
        return None
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return None
    start_value = cast(int, start)
    end_value = cast(int, end)
    return start_value, end_value, score


def _coordinates(
    typed_record: Mapping[str, Any],
    text: str,
) -> tuple[int, int, float] | None:
    try:
        coordinate_values = _raw_coordinates(typed_record)
    except (KeyError, TypeError):
        return None
    return _valid_coordinates(coordinate_values, text)


def _score_scale(typed_record: Mapping[str, Any], fallback: str) -> str:
    score_scale = typed_record.get("score_scale", fallback)
    if not isinstance(score_scale, str) or not score_scale.strip():
        return fallback
    return score_scale


def _region(
    typed_record: Mapping[str, Any],
    observation: TextObservation,
) -> TextRegion | None:
    region_index = typed_record.get("region_index")
    if (
        isinstance(region_index, int)
        and not isinstance(region_index, bool)
        and observation.regions is not None
        and _START_INDEX <= region_index < len(observation.regions)
    ):
        return observation.regions[region_index]
    explicit_region = typed_record.get("region")
    if isinstance(explicit_region, TextRegion):
        return explicit_region
    return None
