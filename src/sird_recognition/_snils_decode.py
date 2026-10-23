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


_REDUCED_DECODES = (
    (1, cv2.IMREAD_COLOR),
    (2, cv2.IMREAD_REDUCED_COLOR_2),
    (4, cv2.IMREAD_REDUCED_COLOR_4),
    (8, cv2.IMREAD_REDUCED_COLOR_8),
)
_PREVIEW_FACTOR, _PREVIEW_FLAG = _REDUCED_DECODES[-1]
_COLOR_NDIM = 3


def _color_raster(payload: np.ndarray, flag: int) -> np.ndarray:
    frame = cv2.imdecode(payload, flag)
    if frame is None or frame.ndim != _COLOR_NDIM or not frame.size:
        raise ValueError("image is not a decodable color raster")
    return frame


def _decode_flag(payload: np.ndarray, max_pixels: int) -> int:
    height, width = _color_raster(payload, _PREVIEW_FLAG).shape[:2]
    # The 1/8 preview rounds sides up, so the estimate is never too small.
    full_pixels = height * width * _PREVIEW_FACTOR * _PREVIEW_FACTOR
    for factor, flag in _REDUCED_DECODES:
        if full_pixels // (factor * factor) <= max_pixels:
            return flag
    raise ValueError("image exceeds pixel limit")


def decode_image(encoded: bytes, limits: ImageLimits) -> np.ndarray:
    """Decode a color raster at the largest scale within the pixel limit."""
    payload = np.frombuffer(encoded, dtype=np.uint8)
    frame = _color_raster(payload, _decode_flag(payload, limits.max_pixels))
    height, width = frame.shape[:2]
    if height * width > limits.max_pixels:
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
