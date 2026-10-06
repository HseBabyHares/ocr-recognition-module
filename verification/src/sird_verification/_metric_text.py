"""Auxiliary character error rate calculation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sird_verification._metric_common import metadata, record
from sird_verification._metric_models import (
    MetricMeasurement,
    MetricRecord,
    MetricStatus,
)


def _edit_row(
    previous: list[int],
    row_index: int,
    reference_character: str,
    hypothesis: str,
) -> list[int]:
    """Build one Levenshtein dynamic-programming row."""
    current = [row_index]
    current.extend(
        min(
            current[-1] + 1,
            previous[hypothesis_index] + 1,
            previous[hypothesis_index - 1]
            + (reference_character != hypothesis_character),
        )
        for hypothesis_index, hypothesis_character in enumerate(
            hypothesis,
            1,
        )
    )
    return current


def _edit_distance(reference: str, hypothesis: str) -> int:
    """Return Levenshtein distance for one reference and hypothesis."""
    previous = list(range(len(hypothesis) + 1))
    for row_index in range(1, len(reference) + 1):
        previous = _edit_row(
            previous,
            row_index,
            reference[row_index - 1],
            hypothesis,
        )
    return previous[-1]


def cer_auxiliary(
    expected: Sequence[str], observed: Sequence[str], **kwargs: Any
) -> MetricRecord:
    """Compute auxiliary character error rate."""
    if len(expected) != len(observed):
        return record(
            MetricMeasurement(
                "cer",
                None,
                None,
                None,
                MetricStatus.BLOCKED,
                "expected and observed lengths differ",
            ),
            metadata(kwargs),
        )
    errors = sum(
        _edit_distance(reference, hypothesis)
        for reference, hypothesis in zip(expected, observed, strict=True)
    )
    characters = sum(len(reference) for reference in expected)
    if characters <= 0:
        metric_metadata = metadata(kwargs)
        return record(
            MetricMeasurement(
                "cer",
                float(errors),
                float(characters),
                None,
                MetricStatus.UNAVAILABLE,
                "reference character denominator is zero",
            ),
            metric_metadata,
        )
    metric_metadata = metadata(kwargs)
    return record(
        MetricMeasurement(
            "cer",
            float(errors),
            float(characters),
            float(errors) / float(characters),
            MetricStatus.AVAILABLE,
            "measurement available",
        ),
        metric_metadata,
    )
