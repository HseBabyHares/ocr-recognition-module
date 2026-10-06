"""Canonical serialization primitives for corpus records."""

from __future__ import annotations

import json
from collections.abc import Mapping
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType
from typing import Any


def _freeze_mapping(mapping: Mapping[Any, Any]) -> MappingProxyType:
    """Freeze mapping members in deterministic key order."""
    frozen_items: list[tuple[str, Any]] = []
    for key, member in mapping.items():
        frozen_items.append((str(key), freeze(member)))
    return MappingProxyType(dict(sorted(frozen_items)))


def freeze(candidate: Any) -> Any:
    """Return a deterministic, immutable representation of ``candidate``."""
    if isinstance(candidate, Mapping):
        return _freeze_mapping(candidate)
    if isinstance(candidate, (list, tuple)):
        return tuple(freeze(member) for member in candidate)
    if isinstance(candidate, set):
        return tuple(sorted(freeze(member) for member in candidate))
    if isinstance(candidate, StrEnum):
        return candidate.value
    return candidate


def jsonable(candidate: Any) -> Any:
    """Convert frozen metadata into JSON-safe canonical data."""
    if isinstance(candidate, Mapping):
        return {
            str(key): jsonable(member) for key, member in candidate.items()
        }
    if isinstance(candidate, (list, tuple)):
        return [jsonable(member) for member in candidate]
    if isinstance(candidate, StrEnum):
        return candidate.value
    return candidate


def digest(candidate: Any) -> str:
    """Return the SHA-256 digest of canonical JSON data."""
    payload = json.dumps(
        jsonable(candidate),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def non_empty(text: str, name: str) -> str:
    """Validate and return a required non-empty string."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"{name} must be non-empty")
    return text
