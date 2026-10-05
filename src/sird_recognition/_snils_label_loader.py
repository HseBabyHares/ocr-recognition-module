"""Validation and caching for packaged OCR labels."""

from __future__ import annotations

import json
from functools import cache
from importlib import resources

from sird_recognition._snils_label_validation import (
    month_values as _month_values,
)
from sird_recognition._snils_label_validation import (
    string_tuple as _string_tuple,
)
from sird_recognition._snils_labels import OcrLabels


def _load_payload() -> object:
    return json.loads(
        resources.files("sird_recognition.resources")
        .joinpath("ocr_labels.json")
        .read_text(encoding="utf-8")
    )


def _parse_payload(payload: object) -> OcrLabels | None:
    if not isinstance(payload, dict):
        return None
    birth_labels = _string_tuple(payload.get("birth_labels"))
    registration_labels = _string_tuple(payload.get("registration_labels"))
    name_tokens = _string_tuple(payload.get("name_label_tokens"))
    months = _month_values(payload.get("months_genitive"))
    if birth_labels is None or registration_labels is None:
        return None
    if name_tokens is None or months is None:
        return None
    return OcrLabels(
        birth_labels,
        registration_labels,
        frozenset(name_tokens),
        months,
    )


@cache
def load_ocr_labels() -> OcrLabels | None:
    """Load and validate the packaged OCR labels once."""
    try:
        payload = _load_payload()
    except Exception:
        return None
    try:
        return _parse_payload(payload)
    except Exception:
        return None
