"""Saved prediction parsing helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sird_experiment.models import PredictionRecord


def coerce_record(
    saved_record: PredictionRecord | Mapping[str, Any],
    schema_version: str,
) -> PredictionRecord:
    if isinstance(saved_record, PredictionRecord):
        return saved_record
    if isinstance(saved_record, Mapping):
        record_fields = dict(saved_record)
        record_fields.setdefault("schema_version", schema_version)
        return PredictionRecord(**record_fields)
    raise TypeError(
        "saved predictions must be PredictionRecord or mapping values"
    )


def first_present(payload: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for field_name in keys:
        if field_name in payload:
            return payload.get(field_name)
    return payload
