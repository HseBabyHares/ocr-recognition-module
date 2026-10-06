"""Shared construction and rate calculations for metrics."""

from __future__ import annotations

from typing import Any

from sird_verification._metric_models import (
    MetricMeasurement,
    MetricMetadata,
    MetricRecord,
    MetricStatus,
    MetricStratum,
)

_UNSPECIFIED = "unspecified"


def record(
    measurement: MetricMeasurement,
    metric_metadata: MetricMetadata,
) -> MetricRecord:
    """Attach comparison metadata to a numerical measurement."""
    return MetricRecord(
        metric=measurement.metric,
        corpus=metric_metadata.corpus,
        corpus_version=metric_metadata.corpus_version,
        variant=metric_metadata.variant,
        mode=metric_metadata.mode,
        form=metric_metadata.form,
        quality_stratum=MetricStratum(metric_metadata.quality_stratum),
        comparison_policy=metric_metadata.comparison_policy,
        evaluator_version=metric_metadata.evaluator_version,
        numerator=measurement.numerator,
        denominator=measurement.denominator,
        value=measurement.metric_value,
        status=measurement.status,
        reason=measurement.reason,
    )


def metadata(arguments: dict[str, Any]) -> MetricMetadata:
    """Extract comparison metadata from metric keyword arguments."""
    return MetricMetadata(
        corpus=arguments.pop("corpus", _UNSPECIFIED),
        corpus_version=arguments.pop("corpus_version", _UNSPECIFIED),
        variant=arguments.pop("variant", _UNSPECIFIED),
        mode=arguments.pop("mode", _UNSPECIFIED),
        form=arguments.pop("form", _UNSPECIFIED),
        quality_stratum=arguments.pop(
            "quality_stratum",
            MetricStratum.UNKNOWN,
        ),
        comparison_policy=arguments.pop(
            "comparison_policy",
            _UNSPECIFIED,
        ),
        evaluator_version=arguments.pop(
            "evaluator_version",
            _UNSPECIFIED,
        ),
    )


def rate(
    name: str,
    numerator: int | float,
    denominator: int | float,
    **kwargs: Any,
) -> MetricRecord:
    metric_metadata = metadata(kwargs)
    if kwargs:
        unexpected = ", ".join(kwargs)
        raise TypeError(f"unexpected arguments: {unexpected}")
    if denominator <= 0:
        measurement = MetricMeasurement(
            name,
            float(numerator),
            float(denominator),
            None,
            MetricStatus.UNAVAILABLE,
            "denominator is zero or missing",
        )
    elif numerator < 0 or numerator > denominator:
        measurement = MetricMeasurement(
            name,
            float(numerator),
            float(denominator),
            None,
            MetricStatus.BLOCKED,
            "numerator is outside denominator",
        )
    else:
        measurement = MetricMeasurement(
            name,
            float(numerator),
            float(denominator),
            float(numerator) / float(denominator),
            MetricStatus.AVAILABLE,
            "measurement available",
        )
    return record(measurement, metric_metadata)
