"""Document boundary detection and bounded perspective correction."""

from __future__ import annotations

import cv2
import numpy as np

from sird_recognition._snils_geometry_config import _GeometryConfig
from sird_recognition._snils_geometry_document import document_candidates
from sird_recognition._snils_geometry_green import green_candidates
from sird_recognition._snils_geometry_luminance import (
    faded_card_candidates,
    luminance_candidates,
)
from sird_recognition._snils_geometry_warp import (
    corner_points,
    target_size,
    warp_frame,
)
from sird_recognition._snils_types import ImageLimits


def warp_has_content(source: np.ndarray, warped: np.ndarray) -> bool:
    """Reject perspective results that contain no useful image content."""
    source_gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    source_edges = cv2.Canny(
        source_gray,
        _GeometryConfig.canny_low,
        _GeometryConfig.canny_high,
    )
    warped_edges = cv2.Canny(
        warped_gray,
        _GeometryConfig.canny_low,
        _GeometryConfig.canny_high,
    )
    return (
        float(warped_gray.std())
        >= max(
            _GeometryConfig.content_stddev_floor,
            float(source_gray.std()) * _GeometryConfig.content_stddev_ratio,
        )
        and float(np.mean(warped_edges > 0))
        >= _GeometryConfig.content_edge_ratio
        and float(np.mean(source_edges > 0)) > 0
    )


def _best_candidate(
    candidates: list[tuple[float, np.ndarray]],
) -> np.ndarray | None:
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate[0])[1]


def green_document_quad(frame: np.ndarray) -> np.ndarray | None:
    """Find the green SNILS card by color, not a learned detector."""
    return _best_candidate(green_candidates(frame))


def luminance_quad(frame: np.ndarray) -> np.ndarray | None:
    """Find a bright document or a card darker than the paper."""
    candidates = luminance_candidates(frame)
    if candidates:
        return candidates[0]
    # A gray copy of the green card has no color for the green finder.
    return _best_candidate(faded_card_candidates(frame))


def document_quad(frame: np.ndarray) -> np.ndarray | None:
    """Find a large, rectangular document boundary without guessing."""
    return _best_candidate(document_candidates(frame))


def order_points(points: np.ndarray) -> np.ndarray:
    """Order a quadrilateral as top-left, top-right, bottom-right, bottom-left.

    Return the points in stable clockwise order.
    """
    ordered = np.zeros(
        (
            _GeometryConfig.quad_point_count,
            _GeometryConfig.coordinate_dimensions,
        ),
        dtype=np.float32,
    )
    top_left, bottom_right, top_right, bottom_left = corner_points(points)
    ordered[0] = top_left
    ordered[2] = bottom_right
    ordered[1] = top_right
    ordered[3] = bottom_left
    return ordered


def warp(
    frame: np.ndarray, points: np.ndarray, limits: ImageLimits
) -> np.ndarray:
    """Warp a detected document while enforcing output bounds."""
    ordered = order_points(points)
    target_width, target_height = target_size(ordered, limits)
    return warp_frame(frame, ordered, target_width, target_height)
