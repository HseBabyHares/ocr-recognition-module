"""Perspective warp sizing helpers."""

from __future__ import annotations

import math

import cv2
import numpy as np

from sird_recognition._snils_types import ImageLimits

# A card that fills a small part of the frame gives glyphs too small for
# Tesseract; 1600 px on the long side read best on 100-150 dpi page scans.
MIN_LONG_SIDE = 1600


def corner_points(
    points: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return corners ordered by coordinate sums and differences."""
    sums = points.sum(axis=1)
    differences = np.diff(points, axis=1).ravel()
    return (
        points[np.argmin(sums)],
        points[np.argmax(sums)],
        points[np.argmin(differences)],
        points[np.argmax(differences)],
    )


def _upscaled(width: float, height: float) -> tuple[float, float]:
    upscale = max(1.0, MIN_LONG_SIDE / max(width, height, 1.0))
    return width * upscale, height * upscale


def target_size(ordered: np.ndarray, limits: ImageLimits) -> tuple[int, int]:
    """Calculate bounded output dimensions for an ordered quadrilateral."""
    width = max(
        np.linalg.norm(ordered[1] - ordered[0]),
        np.linalg.norm(ordered[2] - ordered[3]),
    )
    height = max(
        np.linalg.norm(ordered[3] - ordered[0]),
        np.linalg.norm(ordered[2] - ordered[1]),
    )
    width, height = _upscaled(width, height)
    target_width = min(limits.max_side, max(1, int(width)))
    target_height = min(limits.max_side, max(1, int(height)))
    if target_width * target_height > limits.max_pixels:
        scale = math.sqrt(limits.max_pixels / (target_width * target_height))
        target_width = max(1, int(target_width * scale))
        target_height = max(1, int(target_height * scale))
    return target_width, target_height


def destination(target_width: int, target_height: int) -> np.ndarray:
    """Return the four destination corners for a perspective transform."""
    return np.array(
        [
            [0, 0],
            [target_width - 1, 0],
            [target_width - 1, target_height - 1],
            [0, target_height - 1],
        ],
        dtype=np.float32,
    )


def warp_frame(
    frame: np.ndarray,
    ordered: np.ndarray,
    target_width: int,
    target_height: int,
) -> np.ndarray:
    """Apply a bounded perspective transform with replicated borders."""
    matrix = cv2.getPerspectiveTransform(
        ordered, destination(target_width, target_height)
    )
    return cv2.warpPerspective(
        frame,
        matrix,
        (target_width, target_height),
        borderMode=cv2.BORDER_REPLICATE,
    )
