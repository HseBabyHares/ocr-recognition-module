"""Safety validation helpers for experiment model metadata."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_FORBIDDEN = frozenset(
    (
        "truth",
        "ground_truth",
        "reference",
        "expected",
        "label",
        "labels",
        "personal_value",
        "personal_values",
        "document_bytes",
    )
)
_PROTECTED_TOKENS = ("truth", "ground_truth", "personal")


def _check_mapping_safety(mapping: Mapping[Any, Any], path: str) -> None:
    for key, member in mapping.items():
        _check_mapping_key(key, path)
        child_path = f"{path}.{key}" if path else str(key)
        _check_safe(member, child_path)


def _is_protected_key(key_text: str) -> bool:
    return key_text in _FORBIDDEN or any(
        token in key_text for token in _PROTECTED_TOKENS
    )


def _check_mapping_key(key: Any, path: str) -> None:
    key_text = str(key).lower().replace("-", "_")
    if not _is_protected_key(key_text):
        return
    location = path or "record"
    raise ValueError(
        f"protected truth or personal data is not allowed in {location}"
    )


def _check_safe(candidate: Any, path: str = "") -> None:
    if isinstance(candidate, Mapping):
        _check_mapping_safety(candidate, path)
    elif isinstance(candidate, (list, tuple, set, frozenset)):
        _check_sequence_safety(candidate, path)
    elif isinstance(candidate, (bytes, bytearray, memoryview)):
        raise ValueError(
            "document bytes are not allowed in experiment records"
        )


def _check_sequence_safety(sequence: Any, path: str) -> None:
    for index, member in enumerate(sequence):
        _check_safe(member, f"{path}[{index}]")


def _text(candidate: str, name: str) -> str:
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError(f"{name} must be non-empty")
    return candidate
