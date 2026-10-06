"""Validation and canonicalization stages for experiment records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sird_experiment._model_safety import _check_safe, _text
from sird_experiment._model_serialization import _digest, _freeze

if TYPE_CHECKING:
    from sird_experiment._model_records import (
        PredictionRecord,
        SampleExecutionRecord,
    )


def _validate_execution_identity(record: SampleExecutionRecord) -> None:
    _text(record.run_id, "run_id")
    _text(record.sample_id, "sample_id")
    _text(record.variant_id, "variant_id")
    if record.repeat_id < 0:
        raise ValueError("repeat_id must be non-negative")


def _normalize_execution(record: SampleExecutionRecord) -> None:
    _check_safe(record.applied_execution)
    _check_safe(record.stage_records)
    _check_safe(record.provenance)
    object.__setattr__(
        record, "applied_execution", _freeze(dict(record.applied_execution))
    )
    object.__setattr__(
        record,
        "stage_records",
        tuple(_freeze(dict(stage)) for stage in record.stage_records),
    )
    object.__setattr__(record, "provenance", _freeze(dict(record.provenance)))
    object.__setattr__(record, "assistance", tuple(record.assistance))
    object.__setattr__(record, "test_doubles", tuple(record.test_doubles))


def _validate_prediction_identity(record: PredictionRecord) -> None:
    _text(record.sample_id, "sample_id")
    _text(record.variant_id, "variant_id")
    _text(record.schema_version, "schema_version")
    _text(record.input_checksum, "input_checksum")
    if record.repeat_id < 0:
        raise ValueError("repeat_id must be non-negative")


def _normalize_prediction(record: PredictionRecord) -> None:
    _check_safe(record.payload)
    _check_safe(record.provenance)
    payload = _freeze(dict(record.payload))
    object.__setattr__(record, "payload", payload)
    object.__setattr__(record, "provenance", _freeze(dict(record.provenance)))
    object.__setattr__(record, "assistance", tuple(record.assistance))
    object.__setattr__(record, "test_doubles", tuple(record.test_doubles))
    computed = _digest(
        {"schema_version": record.schema_version, "payload": payload}
    )
    if (
        record.prediction_checksum is not None
        and record.prediction_checksum != computed
    ):
        raise ValueError("prediction_checksum does not match payload")
    object.__setattr__(record, "prediction_checksum", computed)
