from __future__ import annotations

import cv2
import numpy as np

from sird_recognition._snils_checks import ServiceConfig
from sird_recognition._snils_decode import decode_image
from sird_recognition._snils_types import ImageLimits

_CHANNELS = 3
_PHONE_WIDTH = 3024
_PHONE_HEIGHT = 4032
_PHONE_GRAY = 200
_REDUCED_MAX_PIXELS = 1_000_000

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


def test_phone_photo_keeps_full_size() -> None:
    decoded = decode_image(_phone_photo_bytes(), _limits())
    assert decoded.shape[:2] == (_PHONE_HEIGHT, _PHONE_WIDTH)


def test_raster_above_pixel_limit_is_reduced() -> None:
    decoded = decode_image(_phone_photo_bytes(), _limits(_REDUCED_MAX_PIXELS))
    assert decoded.shape[0] * decoded.shape[1] <= _REDUCED_MAX_PIXELS
    assert decoded.shape[0] > decoded.shape[1]

