"""Document candidate validation and contour helpers."""

from collections.abc import Sequence

import cv2
import numpy as np

from sird_recognition._snils_geometry_config import (
    _GeometryConfig,
    quad_sides,
    valid_sides,
)
from sird_recognition._snils_geometry_edge_candidates import closed_edges
from sird_recognition._snils_geometry_green import _contour_quad


def _touches_boundary(
    points: np.ndarray, frame_shape: tuple[int, ...]
) -> bool:
    border = max(
        _GeometryConfig.border_min,
        min(frame_shape[:2]) // _GeometryConfig.border_scale,
    )
    height, width = frame_shape[:2]
    return any(
        coordinate_x <= border
        or coordinate_x >= width - _GeometryConfig.boundary_offset - border
        or coordinate_y <= border
        or coordinate_y >= height - _GeometryConfig.boundary_offset - border
        for coordinate_x, coordinate_y in points
    )


def _valid_document_shape(
    shape: tuple[float, np.ndarray],
    image_area: float,
    rectangle_area: float,
    rectangularity: float,
    frame_shape: tuple[int, ...],
) -> bool:
    area, points = shape
    has_area = area >= image_area * _GeometryConfig.document_min_area_ratio
    has_rectangle = (
        rectangle_area > 0
        and rectangularity >= _GeometryConfig.document_rectangularity
    )
    return all(
        (
            has_area,
            has_rectangle,
            not _touches_boundary(points, frame_shape),
            valid_sides(quad_sides(points)),
        )
    )


def _document_shape_candidate(
    shape: tuple[float, np.ndarray] | None,
    image_area: float,
    frame_shape: tuple[int, ...],
) -> tuple[float, np.ndarray] | None:
    if shape is None:
        return None
    area, points = shape
    rectangle_area = cv2.contourArea(cv2.boxPoints(cv2.minAreaRect(points)))
    rectangularity = area / rectangle_area if rectangle_area > 0 else 0
    if not _valid_document_shape(
        shape,
        image_area,
        rectangle_area,
        rectangularity,
        frame_shape,
    ):
        return None
    return (area / image_area) * rectangularity, points


def _document_candidate(
    contour: np.ndarray,
    epsilon_ratio: float,
    image_area: float,
    frame_shape: tuple[int, ...],
) -> tuple[float, np.ndarray] | None:
    return _document_shape_candidate(
        _contour_quad(contour, epsilon_ratio),
        image_area,
        frame_shape,
    )


def _contour_candidates(
    contours: Sequence[np.ndarray],
    image_area: float,
    frame_shape: tuple[int, ...],
) -> list[tuple[float, np.ndarray]]:
    candidates: list[tuple[float, np.ndarray]] = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[
        : _GeometryConfig.document_contour_limit
    ]:
        for epsilon_ratio in _GeometryConfig.document_epsilon_ratios:
            candidate = _document_candidate(
                contour, epsilon_ratio, image_area, frame_shape
            )
            if candidate is not None:
                candidates.append(candidate)
    return candidates


def _edge_candidates(
    frame: np.ndarray,
    gray: np.ndarray,
    edge_pair: tuple[int, int],
    image_area: float,
) -> list[tuple[float, np.ndarray]]:
    edges = closed_edges(frame, gray, edge_pair)
    contours, _ = cv2.findContours(
        edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    return _contour_candidates(contours, image_area, frame.shape)
