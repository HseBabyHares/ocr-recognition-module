"""SNILS recognition service and its stable public method surface."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import cast

import cv2

from sird_recognition._snils_checks import (
    ServiceConfig,
    is_valid_snils,
    normalize_snils,
)
from sird_recognition._snils_compat import private_helper, refused_result
from sird_recognition._snils_decode import (
    decode_image,
    perspective_image,
    validate_input,
)
from sird_recognition._snils_flow import RecognitionInputs, recognize_variants
from sird_recognition._snils_images import image_variants
from sird_recognition._snils_types import (
    ImageLimits,
    SnilsRecognitionResult,
    SnilsTextReader,
)
from sird_recognition.candidate_extraction import CandidateExtractor


def _validate_cpu_threads(cpu_threads: object) -> int:
    if not isinstance(cpu_threads, int) or isinstance(cpu_threads, bool):
        raise ValueError("cpu_threads must be a positive integer")
    if cpu_threads <= 0:
        raise ValueError("cpu_threads must be a positive integer")
    return cpu_threads


def _validate_limits(limits: ImageLimits) -> ImageLimits:
    if any(
        not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0
        for limit in (
            limits.max_input_bytes,
            limits.max_pixels,
            limits.max_side,
            limits.max_variants,
        )
    ):
        raise ValueError("image limits must be positive integers")
    return limits


def _limits_from_settings(
    settings: dict[str, object],
) -> tuple[int, ImageLimits]:
    """Validate constructor settings and return normalized limits."""
    cpu_threads = settings.pop("cpu_threads", 1)
    limits = ImageLimits(
        cast(
            int, settings.pop("max_input_bytes", ServiceConfig.max_input_bytes)
        ),
        cast(int, settings.pop("max_pixels", ServiceConfig.max_pixels)),
        cast(int, settings.pop("max_side", ServiceConfig.max_side)),
        cast(
            int,
            settings.pop("max_variants", ServiceConfig.default_max_variants),
        ),
    )
    if settings:
        unexpected = next(iter(settings))
        raise TypeError(f"unexpected setting: {unexpected}")
    return _validate_cpu_threads(cpu_threads), _validate_limits(limits)


class SnilsRecognitionService:
    """Preprocess bounded camera images and extract verified SNILS data."""

    def __init__(
        self,
        reader: SnilsTextReader,
        *,
        candidate_extractor: CandidateExtractor | None = None,
        **settings: object,
    ) -> None:
        cpu_threads, limits = _limits_from_settings(settings)
        self._reader = reader
        self._candidate_extractor = candidate_extractor
        self._cpu_threads = cpu_threads
        self._limits = limits

    def preprocess_image(self, image_bytes: bytes) -> tuple[bytes, ...]:
        """Return bounded PNG variants, refusing malformed images."""
        encoded = validate_input(image_bytes, self._limits)
        frame = decode_image(encoded, self._limits)
        prepared = perspective_image(frame, self._limits)
        return image_variants(prepared, self._limits.max_variants)

    def recognize_image(
        self,
        image_bytes: bytes,
        *,
        timeout_seconds: float,
        language: str = "rus+eng",
    ) -> SnilsRecognitionResult:
        """Run local OCR variants and return verified data or refusal."""
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        if not isinstance(language, str) or not language.strip():
            raise ValueError("language must be non-empty")
        try:
            variants = self.preprocess_image(image_bytes)
        except (ValueError, cv2.error):
            return refused_result(("invalid_image",), 0, 0)
        return recognize_variants(
            RecognitionInputs(
                self._reader,
                self._candidate_extractor,
                variants,
                timeout_seconds,
                language,
                self._cpu_threads,
            )
        )

    @classmethod
    def normalize_snils(cls, candidate: str) -> str | None:
        """Normalize one formatted SNILS candidate without repairing digits."""
        return normalize_snils(candidate)

    @classmethod
    def is_valid_snils(cls, candidate: str) -> bool:
        """Validate all eleven digits using the official SNILS checksum."""
        return is_valid_snils(candidate)

    def __getattr__(self, name: str) -> Callable[..., object]:
        """Retain historical private helper access for callers and tests."""
        return private_helper(name, self._limits)
