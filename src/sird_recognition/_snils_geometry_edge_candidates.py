"""Edge preparation for document contour detection."""

from __future__ import annotations

import cv2
import numpy as np

from sird_recognition._snils_geometry_config import _GeometryConfig


def closed_edges(
    frame: np.ndarray,
    gray: np.ndarray,
    edge_pair: tuple[int, int],
) -> np.ndarray:
    """Run edge detection and close small gaps in the edge mask."""
    edges = cv2.Canny(gray, *edge_pair)
    kernel_size = max(
        _GeometryConfig.document_kernel_min,
        min(frame.shape[:2]) // _GeometryConfig.document_kernel_scale,
    )
    if kernel_size % _GeometryConfig.odd_divisor == 0:
        kernel_size += 1
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (kernel_size, kernel_size)
    )
    return cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
