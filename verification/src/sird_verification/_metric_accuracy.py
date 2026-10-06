"""Exact and boolean-rate metric functions."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sird_verification._metric_common import metadata, rate, record
from sird_verification._metric_models import (
    MetricMeasurement,
    MetricRecord,
    MetricStatus,
)


def _blocked(
    name: str,
    reason: str,
    arguments: dict[str, Any],
) -> MetricRecord:
    """Build a blocked result for incompatible sequences."""
    return record(
        MetricMeasurement(
            name, None, None, None, MetricStatus.BLOCKED, reason
        ),
        metadata(arguments),
    )


def _sequence_accuracy(
    name: str,
    expected: Sequence[Any],
    observed: Sequence[Any],
    arguments: dict[str, Any],
) -> MetricRecord:
    """Compute exact matches for two source-grouped sequences."""
    if len(expected) != len(observed):
        return _blocked(
            name,
            "expected and observed lengths differ",
            arguments,
        )
    matches = sum(
        expected_value == observed_value
        for expected_value, observed_value in zip(
            expected,
            observed,
            strict=True,
        )
    )
    return rate(name, matches, len(expected), **arguments)


def exact_field_accuracy(
    expected: Sequence[Any], observed: Sequence[Any], **kwargs: Any
) -> MetricRecord:
    """Compute exact field matches; inputs are already source-grouped."""
    return _sequence_accuracy(
        "exact_field_accuracy",
        expected,
        observed,
        kwargs,
    )


def refusal_rate(refused: Sequence[bool], **kwargs: Any) -> MetricRecord:
    """Compute the proportion of refused observations."""
    return rate(
        "refusal_rate",
        sum(bool(refusal) for refusal in refused),
        len(refused),
        **kwargs,
    )


def false_output_rate(
    false_outputs: Sequence[bool], **kwargs: Any
) -> MetricRecord:
    """Compute the proportion of false outputs."""
    return rate(
        "false_output_rate",
        sum(bool(false_output) for false_output in false_outputs),
        len(false_outputs),
        **kwargs,
    )


def corruption_rate(corrupted: Sequence[bool], **kwargs: Any) -> MetricRecord:
    """Compute the proportion of corrupted observations."""
    return rate(
        "corruption_rate",
        sum(bool(corrupted_item) for corrupted_item in corrupted),
        len(corrupted),
        **kwargs,
    )


def form_accuracy(
    expected: Sequence[Any], observed: Sequence[Any], **kwargs: Any
) -> MetricRecord:
    """Compute exact form matches."""
    return _sequence_accuracy("form_accuracy", expected, observed, kwargs)
