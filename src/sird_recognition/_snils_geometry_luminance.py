"""Bright-document boundary candidates."""

from __future__ import annotations

import cv2
import numpy as np

from sird_recognition._snils_geometry_config import (
    _GeometryConfig,
    quad_sides,
    valid_sides,
)
from sird_recognition._snils_geometry_green import (
    _contour_quad,
    _mask_candidates,
)
from sird_recognition._snils_geometry_mask import _cleaned_mask


def _luminance_mask(frame: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    threshold = int(np.median(gray))
    mask = cv2.inRange(
        gray,
        threshold + _GeometryConfig.luminance_threshold_offset,
        _GeometryConfig.threshold_max_value,
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
                _GeometryConfig.luminance_close_kernel,
                _GeometryConfig.luminance_close_kernel,
            ),
            np.uint8,
        ),
    )


def _luminance_candidate(
    contour: np.ndarray, image_area: float
) -> np.ndarray | None:
    shape = _contour_quad(contour, _GeometryConfig.green_epsilon_ratio)
    if shape is None:
        return None
    area, points = shape
    if area < image_area * _GeometryConfig.luminance_min_area_ratio:
        return None
    if not valid_sides(quad_sides(points)):
        return None
    return points


def luminance_candidates(frame: np.ndarray) -> list[np.ndarray]:
    """Return usable bright-document quadrilaterals."""
    mask = _luminance_mask(frame)
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    image_area = float(frame.shape[0] * frame.shape[1])
    return [
        candidate
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[
            : _GeometryConfig.luminance_contour_limit
        ]
        for candidate in (_luminance_candidate(contour, image_area),)
        if candidate is not None
    ]


def faded_card_candidates(
    frame: np.ndarray,
) -> list[tuple[float, np.ndarray]]:
    """Return card candidates darker than the paper around them.

    shortcut: the frame median is the paper only while the card covers
    less than half of the frame; a close-up of a gray copy is not found.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    paper = int(np.median(gray)) - _GeometryConfig.faded_card_offset
    mask = np.where(gray < paper, _GeometryConfig.threshold_max_value, 0)
    return _mask_candidates(frame, _cleaned_mask(mask.astype(np.uint8)))
