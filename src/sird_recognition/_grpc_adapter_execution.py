"""Execution metadata translation helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sird_recognition import _grpc_adapter_contract as _contract


def map_execution(target: Any, execution: Mapping[str, object]) -> None:
    metadata = dict(execution)
    nested_execution = execution.get("profile_execution")
    if isinstance(nested_execution, Mapping):
        metadata.update(nested_execution)
    if _contract.CALIBRATION_VERSION_KEY not in metadata:
        calibration_ref = metadata.get("calibration_ref")
        if isinstance(calibration_ref, str):
            metadata[_contract.CALIBRATION_VERSION_KEY] = calibration_ref
    _map_text_metadata(target, metadata)
    _map_number_metadata(target, metadata)
    cache_hit = metadata.get("cache_hit")
    if isinstance(cache_hit, bool):
        target.cache_hit = cache_hit


def _map_text_metadata(
    target: Any,
    metadata: Mapping[str, object],
) -> None:
    for source_name in (
        "applied_execution_ref",
        "specification_hash",
        "implementation_version",
        "model_version",
        _contract.CALIBRATION_VERSION_KEY,
        "device",
    ):
        metadata_entry = metadata.get(source_name)
        if isinstance(metadata_entry, str):
            setattr(target, source_name, metadata_entry)


def _map_number_metadata(
    target: Any,
    metadata: Mapping[str, object],
) -> None:
    for field_name in ("elapsed_ms", "model_calls"):
        metadata_entry = metadata.get(field_name)
        if (
            isinstance(metadata_entry, int)
            and not isinstance(metadata_entry, bool)
            and metadata_entry >= 0
        ):
            setattr(target, field_name, metadata_entry)
