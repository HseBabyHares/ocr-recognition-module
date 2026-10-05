"""Green-card boundary candidates."""

from __future__ import annotations

import cv2
import numpy as np

from sird_recognition._snils_geometry_config import (
    _GeometryConfig,
    quad_sides,
    valid_sides,
)


def _contour_quad(
    contour: np.ndarray, epsilon: float
) -> tuple[float, np.ndarray] | None:
    perimeter = cv2.arcLength(contour, True)
    if perimeter <= 0:
        return None
    polygon = cv2.approxPolyDP(contour, epsilon * perimeter, True)
    if len(polygon) != _GeometryConfig.quad_point_count:
        return None
    if not cv2.isContourConvex(polygon):
        return None
    points = polygon.reshape(
        _GeometryConfig.quad_point_count,
        _GeometryConfig.coordinate_dimensions,
    ).astype(np.float32)
    return cv2.contourArea(contour), points


def _green_shape_candidate(
    shape: tuple[float, np.ndarray] | None,
    image_area: float,
) -> tuple[float, np.ndarray] | None:
    if shape is None:
        return None
    area, points = shape
    rectangle_area = cv2.contourArea(cv2.boxPoints(cv2.minAreaRect(points)))
    rectangularity = area / rectangle_area if rectangle_area > 0 else 0
    is_valid = (
        area >= image_area * _GeometryConfig.green_min_area_ratio
        and rectangle_area > 0
        and rectangularity >= _GeometryConfig.green_rectangularity
        and valid_sides(quad_sides(points))
    )
    return (
        (
            (area / image_area) * rectangularity,
            points,
        )
        if is_valid
        else None
    )


def _green_candidate(
    contour: np.ndarray, image_area: float
) -> tuple[float, np.ndarray] | None:
    return _green_shape_candidate(
        _contour_quad(contour, _GeometryConfig.green_epsilon_ratio),
        image_area,
    )


def _green_mask(frame: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(
        hsv, _GeometryConfig.green_hsv_low, _GeometryConfig.green_hsv_high
    )
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        np.ones(
            (
                _GeometryConfig.morph_open_kernel,
                _GeometryConfig.morph_open_kernel,
            ),
            np.uint8,
        ),
    )
    return cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        np.ones(
            (
                _GeometryConfig.morph_close_kernel,
                _GeometryConfig.morph_close_kernel,
            ),
            np.uint8,
        ),
    )


def green_candidates(frame: np.ndarray) -> list[tuple[float, np.ndarray]]:
    """Return usable green document candidates in contour order."""
    mask = _green_mask(frame)
    image_area = float(frame.shape[0] * frame.shape[1])
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    return [
        candidate
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[
            : _GeometryConfig.green_contour_limit
        ]
        for candidate in (_green_candidate(contour, image_area),)
        if candidate is not None
    ]
