from __future__ import annotations

import cv2
import numpy as np

from sird_recognition._snils_checks import ServiceConfig
from sird_recognition._snils_decode import decode_image
from sird_recognition._snils_geometry import green_document_quad
from sird_recognition._snils_geometry_warp import MIN_LONG_SIDE, target_size
from sird_recognition._snils_types import ImageLimits

_CHANNELS = 3
_PHONE_WIDTH = 3024
_PHONE_HEIGHT = 4032
_PHONE_GRAY = 200
_REDUCED_MAX_PIXELS = 1_000_000
_PAGE_WIDTH = 620
_PAGE_HEIGHT = 877
_PAGE_WHITE = 255
_FADED_CARD_POINTS = (
    (350, 40),
    (590, 45),
    (588, 200),
    (348, 196),
)
# A light green card blended 65% toward white: HSV saturation is below 20.
_FADED_CARD_COLOR = (225, 239, 230)
# Neutral, warm, and cool white balance as BGR channel gains.
# Gains stay at or below 1: a cast must not clip the paper and the card.
_NEUTRAL_CAST = (1.0, 1.0, 1.0)
_WARM_CAST = (0.7, 0.87, 1.0)
_COOL_CAST = (1.0, 0.87, 0.74)
_COLOR_CASTS = (_NEUTRAL_CAST, _WARM_CAST, _COOL_CAST)
_FADED_CARD_MIN_RATIO = 0.06
_FADED_CARD_MAX_RATIO = 0.08


def _limits(max_pixels: int = ServiceConfig.max_pixels) -> ImageLimits:
    return ImageLimits(
        ServiceConfig.max_input_bytes,
        max_pixels,
        ServiceConfig.max_side,
        ServiceConfig.default_max_variants,
    )


def _phone_photo_bytes() -> bytes:
    image = np.full(
        (_PHONE_HEIGHT, _PHONE_WIDTH, _CHANNELS), _PHONE_GRAY, dtype=np.uint8
    )
    return cv2.imencode(".jpg", image)[1].tobytes()


def _faded_card_page(gains: tuple[float, float, float]) -> np.ndarray:
    page = np.full(
        (_PAGE_HEIGHT, _PAGE_WIDTH, _CHANNELS), _PAGE_WHITE, dtype=np.uint8
    )
    points = np.array(_FADED_CARD_POINTS, dtype=np.int32)
    cv2.fillPoly(page, [points], _FADED_CARD_COLOR)
    cast_page = page.astype(np.float32) * np.array(gains, np.float32)
    return np.clip(cast_page, 0, _PAGE_WHITE).astype(np.uint8)


def test_phone_photo_keeps_full_size() -> None:
    decoded = decode_image(_phone_photo_bytes(), _limits())
    assert decoded.shape[:2] == (_PHONE_HEIGHT, _PHONE_WIDTH)


def test_raster_above_pixel_limit_is_reduced() -> None:
    decoded = decode_image(_phone_photo_bytes(), _limits(_REDUCED_MAX_PIXELS))
    assert decoded.shape[0] * decoded.shape[1] <= _REDUCED_MAX_PIXELS
    assert decoded.shape[0] > decoded.shape[1]


def test_faded_green_card_under_color_cast() -> None:
    for gains in _COLOR_CASTS:
        quad = green_document_quad(_faded_card_page(gains))
        assert quad is not None
        ratio = cv2.contourArea(quad) / (_PAGE_WIDTH * _PAGE_HEIGHT)
        assert _FADED_CARD_MIN_RATIO <= ratio <= _FADED_CARD_MAX_RATIO


def test_small_card_warp_is_upscaled() -> None:
    ordered = np.array(_FADED_CARD_POINTS, dtype=np.float32)

    width, height = target_size(ordered, _limits())
    reduced = target_size(ordered, _limits(_REDUCED_MAX_PIXELS))

    assert max(width, height) >= MIN_LONG_SIDE
    assert reduced[0] * reduced[1] <= _REDUCED_MAX_PIXELS
