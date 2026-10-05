"""Input validation, decoding, and document perspective selection."""

from __future__ import annotations

import cv2
import numpy as np

from sird_recognition._snils_geometry import (
    document_quad,
    green_document_quad,
    luminance_quad,
    warp,
    warp_has_content,
)
from sird_recognition._snils_types import ImageLimits


def validate_input(image_bytes: bytes, limits: ImageLimits) -> bytes:
    """Validate compressed image bytes against the configured bound."""
    if not isinstance(image_bytes, bytes) or not image_bytes:
        raise ValueError("image must be non-empty bytes")
    if len(image_bytes) > limits.max_input_bytes:
        raise ValueError("image exceeds byte limit")
    return image_bytes


def _resized_dimensions(
    width: int, height: int, scale: float
) -> tuple[int, int]:
    resized_width = max(1, int(width * scale))
    resized_height = max(1, int(height * scale))
    return resized_width, resized_height


def _resize_frame(frame: np.ndarray, limits: ImageLimits) -> np.ndarray:
    height, width = frame.shape[:2]
    if max(height, width) <= limits.max_side:
        return frame
    scale = limits.max_side / max(height, width)
    resized_width, resized_height = _resized_dimensions(width, height, scale)
    return cv2.resize(
        frame,
        (resized_width, resized_height),
        interpolation=cv2.INTER_AREA,
    )


def decode_image(encoded: bytes, limits: ImageLimits) -> np.ndarray:
    """Decode a color raster and apply pixel and side limits."""
    payload = np.frombuffer(encoded, dtype=np.uint8)
    frame = cv2.imdecode(payload, cv2.IMREAD_COLOR)
    if frame is None or frame.ndim != 3:
        raise ValueError("image is not a decodable color raster")
    height, width = frame.shape[:2]
    if height <= 0 or width <= 0 or height * width > limits.max_pixels:
        raise ValueError("image exceeds pixel limit")
    return _resize_frame(frame, limits)


def perspective_image(frame: np.ndarray, limits: ImageLimits) -> np.ndarray:
    """Select and apply the first usable document quadrilateral."""
    points = green_document_quad(frame)
    if points is None:
        points = document_quad(frame)
    if points is None:
        points = luminance_quad(frame)
    if points is None:
        return frame
    warped = warp(frame, points, limits)
    return warped if warp_has_content(frame, warped) else frame
