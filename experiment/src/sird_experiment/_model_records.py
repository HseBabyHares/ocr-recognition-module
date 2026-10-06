"""Immutable execution, prediction, evaluation, and selection records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, cast

from sird_experiment._dataclass_fields import (
    _DataclassFieldSpec,
    _inject_dataclass_fields,
)
from sird_experiment._model_enums import (
    ExperimentMode,
    ExperimentStatus,
    SampleStatus,
)
from sird_experiment._model_safety import _check_safe, _text
from sird_experiment._model_serialization import _freeze
from sird_experiment._record_helpers import (
    _normalize_execution,
    _normalize_prediction,
    _validate_execution_identity,
    _validate_prediction_identity,
)


def _status_reason(status: ExperimentStatus | SampleStatus) -> str:
    return status.value


def _freeze_exclusion_reasons(
    exclusions: Mapping[str, tuple[str, ...]],
) -> Mapping[str, tuple[str, ...]]:
    return _freeze(
        {
            variant_id: tuple(exclusion_reasons)
            for variant_id, exclusion_reasons in exclusions.items()
        }
    )


_MODEL_MODULE = "sird_experiment.models"
_STATUS_FIELD = "status"


@dataclass(frozen=True, slots=True)
class SampleExecutionRecord:
    """One terminal record for one planned sample/variant/repeat pair."""

    __module__ = _MODEL_MODULE
    run_id: str
    sample_id: str
    variant_id: str
    repeat_id: int
    mode: ExperimentMode | str
    status: SampleStatus | str
    input_checksum: str | None = None
    resolved_spec_hash: str | None = None
    assistance: tuple[str, ...] = ()
    test_doubles: tuple[str, ...] = ()
    applied_execution: Mapping[str, Any] = field(default_factory=dict)
    module_result_ref: str | None = None
    stage_records: tuple[Mapping[str, Any], ...] = ()
    reason: str = ""
    failed_stage: str | None = None
    wall_time_ms: float | None = None
    cpu_time_ms: float | None = None
    peak_rss_bytes: int | None = None
    gpu_peak_bytes: int | None = None
    cache_hits: int = 0
    warmup_state: str | None = None
    provenance: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_execution_identity(self)
        status = SampleStatus(self.status)
        object.__setattr__(self, "mode", ExperimentMode(self.mode))
        object.__setattr__(self, _STATUS_FIELD, status)
        _normalize_execution(self)
        if not self.reason.strip():
            object.__setattr__(self, "reason", _status_reason(status))

    @property
    def terminal(self) -> bool:
        return True


@dataclass(frozen=True, slots=True)
class PredictionRecord:
    """Saved, truth-free prediction data for one planned pair."""

    __module__ = _MODEL_MODULE
    sample_id: str
    variant_id: str
    repeat_id: int
    schema_version: str
    payload: Mapping[str, Any]
    input_checksum: str
    prediction_checksum: str | None = None
    resolved_spec_hash: str | None = None
    provenance: Mapping[str, str] = field(default_factory=dict)
    assistance: tuple[str, ...] = ()
    test_doubles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_prediction_identity(self)
        _normalize_prediction(self)

    @classmethod
    def from_payload(cls, **kwargs: Any) -> PredictionRecord:
        return cls(**kwargs)


@dataclass(frozen=True, slots=True)
@_inject_dataclass_fields
class EvaluationRecord:
    """Bounded metric evidence. Truth is represented only by its checksum."""

    __module__ = _MODEL_MODULE
    variant_id: str
    metric: str
    status: ExperimentStatus | str
    evaluator_version: str = "1"
    normalization_policy: str = "identity"
    stratum: str = "all"
    unit: str = "sample"
    numerator: int | float | None = None
    denominator: int | float | None = None
    _value_field = _DataclassFieldSpec(
        "value",
        float | None,
        None,
        "denominator",
    )
    prediction_hash: str | None = None
    truth_hash: str | None = None
    reason: str = ""
    exclusions: tuple[str, ...] = ()
    provenance: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _text(self.variant_id, "variant_id")
        _text(self.metric, "metric")
        _text(self.evaluator_version, "evaluator_version")
        status = ExperimentStatus(self.status)
        object.__setattr__(self, _STATUS_FIELD, status)
        _check_safe(self.provenance)
        object.__setattr__(self, "provenance", _freeze(dict(self.provenance)))
        object.__setattr__(self, "exclusions", tuple(self.exclusions))
        if not self.reason.strip():
            object.__setattr__(self, "reason", _status_reason(status))
        if self.denominator is not None and self.denominator < 0:
            raise ValueError("denominator must not be negative")

    @property
    def passed(self) -> bool:
        return cast(ExperimentStatus, self.status) is ExperimentStatus.PASS


@dataclass(frozen=True, slots=True)
class SelectionDecision:
    """Selection evidence with explicit hard-boundary exclusions."""

    __module__ = _MODEL_MODULE
    status: ExperimentStatus | str
    selected_variant_id: str | None
    considered_variants: tuple[str, ...]
    exclusions: Mapping[str, tuple[str, ...]]
    non_dominated_variants: tuple[str, ...]
    hard_boundaries: Mapping[str, Any]
    rule: str
    reason: str = ""

    def __post_init__(self) -> None:
        status = ExperimentStatus(self.status)
        object.__setattr__(self, _STATUS_FIELD, status)
        object.__setattr__(
            self, "considered_variants", tuple(self.considered_variants)
        )
        object.__setattr__(
            self, "non_dominated_variants", tuple(self.non_dominated_variants)
        )
        object.__setattr__(
            self, "exclusions", _freeze_exclusion_reasons(self.exclusions)
        )
        object.__setattr__(
            self, "hard_boundaries", _freeze(dict(self.hard_boundaries))
        )
        _text(self.rule, "rule")
        if (
            self.selected_variant_id is not None
            and self.selected_variant_id not in self.non_dominated_variants
        ):
            raise ValueError("selected variant must be non-dominated")

    @property
    def selected(self) -> str | None:
        return self.selected_variant_id
