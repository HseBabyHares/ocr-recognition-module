"""Bounded OpenCV image preprocessing for SNILS cards."""

from __future__ import annotations

import cv2
import numpy as np


class _ImageConfig:
    """Image constants kept together to avoid accidental drift."""

    clahe_clip_limit = 2.0
    clahe_tile_size = 8
    threshold_max_value = 255
    adaptive_block_size = 31
    adaptive_c = 11
    glare_low = 245
    glare_high = 255
    morph_small_kernel = 3
    morph_open_kernel = 9
    morph_close_kernel = 31
    glare_area_ratio = 0.25
    inpaint_radius = 3


def encode_image(image: np.ndarray) -> bytes:
    """Encode an image as PNG or fail closed."""
    encoded_ok, encoded = cv2.imencode(".png", image)
    if not encoded_ok:
        raise ValueError("preprocessed image encoding failed")
    return encoded.tobytes()


def repair_glare_image(frame: np.ndarray) -> np.ndarray:
    """Repair a bounded amount of glare without changing large images."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mask = cv2.inRange(gray, _ImageConfig.glare_low, _ImageConfig.glare_high)
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        np.ones(
            (_ImageConfig.morph_small_kernel, _ImageConfig.morph_small_kernel),
            np.uint8,
        ),
    )
    mask_size = cv2.countNonZero(mask)
    if (
        mask_size == 0
        or mask_size
        > frame.shape[0] * frame.shape[1] * _ImageConfig.glare_area_ratio
    ):
        return frame
    return cv2.inpaint(
        frame,
        mask,
        _ImageConfig.inpaint_radius,
        cv2.INPAINT_TELEA,
    )


def enhanced_image_variants(frame: np.ndarray) -> tuple[bytes, ...]:
    """Build the contrast and adaptive-threshold variants in order."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(
        clipLimit=_ImageConfig.clahe_clip_limit,
        tileGridSize=(
            _ImageConfig.clahe_tile_size,
            _ImageConfig.clahe_tile_size,
        ),
    )
    enhanced = clahe.apply(gray)
    enhanced_bytes = encode_image(enhanced)
    threshold = cv2.adaptiveThreshold(
        enhanced,
        _ImageConfig.threshold_max_value,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        _ImageConfig.adaptive_block_size,
        _ImageConfig.adaptive_c,
    )
    return enhanced_bytes, encode_image(threshold)


def image_variants(frame: np.ndarray, max_variants: int) -> tuple[bytes, ...]:
    """Build original, glare-repaired, and enhanced variants."""
    variants = [encode_image(frame)]
    repaired = repair_glare_image(frame)
    variants.append(encode_image(repaired))
    variants.extend(enhanced_image_variants(repaired))
    return tuple(variants[:max_variants])
