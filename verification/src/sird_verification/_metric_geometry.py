"""Bounding-box intersection-over-union metric."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sird_verification._metric_common import metadata, rate, record
from sird_verification._metric_models import (
    MetricMeasurement,
    MetricRecord,
    MetricStatus,
)

_GEOMETRY_METRIC = "geometry_iou"


def _valid_box(box: Sequence[float]) -> bool:
    """Return whether a box has four coordinates and positive extents."""
    return (
        len(box) == 4
        and box[2] > box[0]
        and box[3] > box[1]
    )


def _valid_pair(
    left: Sequence[float],
    right: Sequence[float],
) -> bool:
    """Return whether both boxes have usable geometry."""
    return _valid_box(left) and _valid_box(right)


def _overlap(
    left_start: float,
    left_end: float,
    right_start: float,
    right_end: float,
) -> float:
    """Return the overlap between two one-dimensional extents."""
    overlap_start = max(left_start, right_start)
    overlap_end = min(left_end, right_end)
    return max(0, overlap_end - overlap_start)


def _area(box: Sequence[float]) -> float:
    """Return the area of a valid box."""
    width = box[2] - box[0]
    height = box[3] - box[1]
    return width * height


def _box_iou(left: Sequence[float], right: Sequence[float]) -> float | None:
    """Return IoU for valid ``(x1, y1, x2, y2)`` boxes."""
    if not _valid_pair(left, right):
        return None
    intersection = _overlap(
        left[0],
        left[2],
        right[0],
        right[2],
    ) * _overlap(
        left[1],
        left[3],
        right[1],
        right[3],
    )
    return intersection / (_area(left) + _area(right) - intersection)


def geometry_iou(
    expected: Sequence[Sequence[float]],
    observed: Sequence[Sequence[float]],
    **kwargs: Any,
) -> MetricRecord:
    """Compute mean IoU for paired bounding boxes."""
    if len(expected) != len(observed):
        return record(
            MetricMeasurement(
                _GEOMETRY_METRIC,
                None,
                None,
                None,
                MetricStatus.BLOCKED,
                "expected and observed lengths differ",
            ),
            metadata(kwargs),
        )
    iou_scores: list[float] = []
    for left, right in zip(expected, observed, strict=True):
        iou_score = _box_iou(left, right)
        if iou_score is None:
            return record(
                MetricMeasurement(
                    _GEOMETRY_METRIC,
                    None,
                    None,
                    None,
                    MetricStatus.BLOCKED,
                    "invalid box geometry",
                ),
                metadata(kwargs),
            )
        iou_scores.append(iou_score)
    return rate(
        _GEOMETRY_METRIC,
        sum(iou_scores),
        len(iou_scores),
        **kwargs,
    )
