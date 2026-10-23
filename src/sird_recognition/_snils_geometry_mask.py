"""Green-card color masks."""

from __future__ import annotations

import cv2
import numpy as np

from sird_recognition._snils_geometry_config import _GeometryConfig


def _cleaned_mask(mask: np.ndarray) -> np.ndarray:
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


def _white_balanced(frame: np.ndarray) -> np.ndarray:
    channels = frame.shape[2]
    pixels = frame.reshape(-1, channels).astype(np.float32)
    background = np.median(pixels, axis=0)
    gains = background.max() / np.maximum(background, 1.0)
    return np.clip(
        frame.astype(np.float32) * gains,
        0,
        _GeometryConfig.threshold_max_value,
    ).astype(np.uint8)


def _greenness(frame: np.ndarray) -> np.ndarray:
    # Lab a* falls as green rises; a faded card keeps a small, steady offset.
    green_red = cv2.cvtColor(_white_balanced(frame), cv2.COLOR_BGR2LAB)[..., 1]
    return np.clip(
        int(np.median(green_red)) - green_red.astype(np.int16),
        0,
        _GeometryConfig.threshold_max_value,
    ).astype(np.uint8)


def hsv_green_mask(frame: np.ndarray) -> np.ndarray:
    """Mark pixels inside the absolute HSV green range."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    return _cleaned_mask(
        cv2.inRange(
            hsv,
            _GeometryConfig.green_hsv_low,
            _GeometryConfig.green_hsv_high,
        )
    )


def relative_green_mask(frame: np.ndarray) -> np.ndarray:
    """Mark pixels greener than the background after a white balance.

    shortcut: the frame median is the background only while the card covers
    less than half of the frame; for a close-up the HSV mask is the fallback.
    """
    greenness = _greenness(frame)
    otsu, _ = cv2.threshold(
        greenness, 0, _GeometryConfig.threshold_max_value, cv2.THRESH_OTSU
    )
    floor = max(otsu, _GeometryConfig.green_relative_floor)
    return _cleaned_mask(
        np.where(
            greenness >= floor, _GeometryConfig.threshold_max_value, 0
        ).astype(np.uint8)
    )
