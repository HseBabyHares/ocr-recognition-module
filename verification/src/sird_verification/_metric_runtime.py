"""Runtime resource metric functions."""

from __future__ import annotations

from collections.abc import Sequence
from math import ceil, isfinite
from typing import Any

from sird_verification._metric_common import metadata, record
from sird_verification._metric_models import (
    MetricMeasurement,
    MetricRecord,
    MetricStatus,
)

_DEFAULT_PERCENTILE = 99


def latency_percentile(
    samples: Sequence[float],
    percentile: float = _DEFAULT_PERCENTILE,
    **kwargs: Any,
) -> MetricRecord:
    """Return a deterministic nearest-rank latency percentile."""
    metric_metadata = metadata(kwargs)
    if not samples or not 0 <= percentile <= 100:
        return record(
            MetricMeasurement(
                "latency_percentile",
                None,
                len(samples),
                None,
                MetricStatus.BLOCKED,
                "invalid or empty latency samples",
            ),
            metric_metadata,
        )
    if any(not isfinite(sample) or sample < 0 for sample in samples):
        return record(
            MetricMeasurement(
                "latency_percentile",
                None,
                len(samples),
                None,
                MetricStatus.BLOCKED,
                "invalid or empty latency samples",
            ),
            metric_metadata,
        )
    ordered = sorted(samples)
    rank = max(1, ceil(percentile / 100 * len(ordered)))
    selected = ordered[rank - 1]
    return record(
        MetricMeasurement(
            "latency_percentile",
            selected,
            len(ordered),
            selected,
            MetricStatus.AVAILABLE,
            "deterministic nearest-rank percentile",
        ),
        metric_metadata,
    )


def memory_peak(samples: Sequence[float], **kwargs: Any) -> MetricRecord:
    """Return the maximum memory sample."""
    metric_metadata = metadata(kwargs)
    if not samples or any(
        not isfinite(sample) or sample < 0 for sample in samples
    ):
        return record(
            MetricMeasurement(
                "memory_peak",
                None,
                len(samples),
                None,
                MetricStatus.BLOCKED,
                "invalid or empty memory samples",
            ),
            metric_metadata,
        )
    peak = max(samples)
    return record(
        MetricMeasurement(
            "memory_peak",
            peak,
            len(samples),
            peak,
            MetricStatus.AVAILABLE,
            "peak sample available",
        ),
        metric_metadata,
    )
