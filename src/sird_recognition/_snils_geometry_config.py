"""Shared geometry thresholds and quadrilateral primitives."""

from __future__ import annotations

import numpy as np


class _GeometryConfig:
    """Geometry thresholds kept together as immutable policy values."""

    content_stddev_floor = 5.0
    content_stddev_ratio = 0.08
    content_edge_ratio = 0.001
    green_hsv_low = (30, 20, 70)
    green_hsv_high = (110, 255, 255)
    green_min_area_ratio = 0.05
    green_epsilon_ratio = 0.04
    green_rectangularity = 0.45
    green_relative_floor = 4
    max_side_ratio = 8
    luminance_threshold_offset = 1
    luminance_close_kernel = 21
    luminance_min_area_ratio = 0.2
    canny_low = 50
    canny_high = 150
    green_contour_limit = 20
    luminance_contour_limit = 5
    document_contour_limit = 100
    document_edge_pairs = ((20, 80), (30, 100), (50, 150))
    document_kernel_min = 3
    document_kernel_scale = 180
    document_min_area_ratio = 0.2
    document_epsilon_ratios = (0.015, 0.025, 0.04)
    document_rectangularity = 0.75
    border_min = 4
    border_scale = 100
    boundary_offset = 1
    quad_point_count = 4
    threshold_max_value = 255
    morph_open_kernel = 9
    morph_close_kernel = 31
    odd_divisor = 2
    coordinate_dimensions = 2


def quad_sides(points: np.ndarray) -> list[float]:
    """Return the four side lengths of a quadrilateral."""
    return [
        float(
            np.linalg.norm(
                points[index]
                - points[(index + 1) % _GeometryConfig.quad_point_count]
            )
        )
        for index in range(_GeometryConfig.quad_point_count)
    ]


def valid_sides(sides: list[float]) -> bool:
    """Return whether side lengths are positive and similarly scaled."""
    shortest = min(sides)
    return (
        shortest > 0
        and max(sides) / shortest <= _GeometryConfig.max_side_ratio
    )
