"""Stable contracts for SNILS recognition."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from sird_recognition.contracts.text_observation import TextObservation


class SnilsRecognitionStatus(StrEnum):
    """Terminal status of SNILS recognition."""

    VERIFIED = "verified"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class SnilsRecognitionResult:
    """Verified fields, or an explicit refusal with stable diagnostics."""

    status: SnilsRecognitionStatus
    snils_number: str | None
    full_name: str | None
    birth_date: str | None
    diagnostics: tuple[str, ...]
    variant_count: int
    observation_count: int
    birth_place: str | None = None

    @property
    def verified(self) -> bool:
        """Whether the result contains a checksum-valid SNILS."""
        return self.status is SnilsRecognitionStatus.VERIFIED

    @property
    def refused(self) -> bool:
        """Whether evidence was insufficient or conflicting."""
        return self.status is SnilsRecognitionStatus.REFUSED


class SnilsTextReader(Protocol):
    """Minimal local reader interface used by the image pipeline."""

    def read(
        self,
        image: bytes,
        *,
        timeout_seconds: float,
        language: str,
        cpu_threads: int,
    ) -> TextObservation:
        """Read one encoded raster."""


@dataclass(frozen=True, slots=True)
class ImageLimits:
    """Resource limits for bounded image processing."""

    max_input_bytes: int
    max_pixels: int
    max_side: int
    max_variants: int
