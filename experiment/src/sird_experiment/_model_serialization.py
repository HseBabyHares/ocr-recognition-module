"""Canonicalization helpers for experiment models."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Any


def _mapping_key(pair: tuple[Any, Any]) -> str:
    return str(pair[0])


def _frozen_mapping(mapping: Mapping[Any, Any]) -> MappingProxyType:
    frozen_items = {
        str(key): _freeze(member) for key, member in mapping.items()
    }
    return MappingProxyType(frozen_items)


def _freeze(candidate: Any) -> Any:
    if isinstance(candidate, Mapping):
        return _frozen_mapping(candidate)
    if isinstance(candidate, (list, tuple)):
        return tuple(_freeze(element) for element in candidate)
    if isinstance(candidate, (set, frozenset)):
        frozen_members = (_freeze(element) for element in candidate)
        return tuple(sorted(frozen_members, key=repr))
    return candidate


def _jsonable(candidate: Any) -> Any:
    if isinstance(candidate, Mapping):
        return {
            str(key): _jsonable(member)
            for key, member in sorted(candidate.items(), key=_mapping_key)
        }
    if isinstance(candidate, (list, tuple, set, frozenset)):
        return [_jsonable(element) for element in candidate]
    if isinstance(candidate, StrEnum):
        return candidate.value
    return candidate


def _digest(candidate: Any) -> str:
    payload = json.dumps(
        _jsonable(candidate),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
