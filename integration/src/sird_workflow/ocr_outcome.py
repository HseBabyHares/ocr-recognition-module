"""Explicit outcomes returned by the OCR boundary."""

from enum import StrEnum


class OcrOutcome(StrEnum):
    """Explicit outcomes returned by the injected OCR boundary."""

    SUCCESS = "success"
    REJECTED = "rejected"
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    CANCELLED = "cancelled"
    LIMIT = "limit"
