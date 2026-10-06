"""Probability calibration metric."""

from __future__ import annotations

from collections.abc import Sequence
from math import isfinite
from typing import Any

from sird_verification._metric_common import metadata, rate, record
from sird_verification._metric_models import (
    MetricMeasurement,
    MetricRecord,
    MetricStatus,
)


def uncertainty_brier(
    probabilities: Sequence[float],
    outcomes: Sequence[bool],
    **kwargs: Any,
) -> MetricRecord:
    """Compute the mean squared probability error."""
    if len(probabilities) != len(outcomes):
        return record(
            MetricMeasurement(
                "uncertainty_brier",
                None,
                None,
                None,
                MetricStatus.BLOCKED,
                "probabilities and outcomes lengths differ",
            ),
            metadata(kwargs),
        )
    if any(
        not isfinite(probability) or not 0 <= probability <= 1
        for probability in probabilities
    ):
        return record(
            MetricMeasurement(
                "uncertainty_brier",
                None,
                len(probabilities),
                None,
                MetricStatus.BLOCKED,
                "probability outside [0, 1]",
            ),
            metadata(kwargs),
        )
    numerator = sum(
        (probability - bool(outcome)) ** 2
        for probability, outcome in zip(
            probabilities,
            outcomes,
            strict=True,
        )
    )
    return rate("uncertainty_brier", numerator, len(probabilities), **kwargs)
