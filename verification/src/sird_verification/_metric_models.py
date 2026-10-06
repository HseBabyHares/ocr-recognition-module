"""Immutable metric record and measurement types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Any


class MetricStatus(StrEnum):
    """Whether a metric has a usable measurement."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class MetricStratum(StrEnum):
    """Quality stratum attached to a metric record."""

    ALL = "all"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MetricMetadata:
    """Comparison metadata shared by metric observations."""

    corpus: str
    corpus_version: str
    variant: str
    mode: str
    form: str
    quality_stratum: MetricStratum | str
    comparison_policy: str
    evaluator_version: str


@dataclass(frozen=True, slots=True)
class MetricMeasurement:
    """Numerical result before comparison metadata is attached."""

    metric: str
    numerator: float | None
    denominator: float | None
    metric_value: float | None
    status: MetricStatus
    reason: str


_RECORD_FIELDS = (
    "metric",
    "corpus",
    "corpus_version",
    "variant",
    "mode",
    "form",
    "quality_stratum",
    "comparison_policy",
    "evaluator_version",
    "numerator",
    "denominator",
    "value",
    "status",
    "reason",
)


@dataclass(frozen=True, slots=True, init=False)
class MetricRecord:
    """A bounded metric observation with its comparison provenance."""

    metric: str
    corpus: str
    corpus_version: str
    variant: str
    mode: str
    form: str
    quality_stratum: MetricStratum
    comparison_policy: str
    evaluator_version: str
    numerator: float | None
    denominator: float | None
    _metric_value: float | None
    status: MetricStatus
    reason: str

    def __init__(self, *positional: Any, **named: Any) -> None:
        provided = dict(zip(_RECORD_FIELDS, positional, strict=False))
        provided.update(named)
        too_many_positional = len(positional) > len(_RECORD_FIELDS)
        wrong_fields = set(provided) != set(_RECORD_FIELDS)
        if too_many_positional or wrong_fields:
            raise TypeError("metric record arguments do not match its fields")
        for field_name in _RECORD_FIELDS:
            target_name = (
                "_metric_value" if field_name == "value" else field_name
            )
            object.__setattr__(self, target_name, provided[field_name])
        self.__post_init__()

    def __post_init__(self) -> None:
        required_names = (
            "metric",
            "corpus",
            "corpus_version",
            "variant",
            "mode",
            "form",
            "comparison_policy",
            "evaluator_version",
            "reason",
        )
        for field_name in required_names:
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must be non-empty")
        measured_value = self.value
        if measured_value is not None and not isfinite(measured_value):
            raise ValueError("value must be finite")

    @property
    def _measured_value(self) -> float | None:
        """Return the measured value."""
        return self._metric_value

setattr(
    MetricRecord,
    "value",
    property(MetricRecord._measured_value.fget),
)
