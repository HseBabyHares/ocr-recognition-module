"""Validation and normalization for candidate extractor settings."""

import math
from collections.abc import Mapping


def _validate_positive_settings(
    settings: Mapping[str, object],
    setting_names: tuple[str, ...],
) -> None:
    for setting_name in setting_names:
        setting_value = settings[setting_name]
        if (
            isinstance(setting_value, bool)
            or not isinstance(setting_value, int)
            or setting_value <= 0
        ):
            raise ValueError(f"{setting_name} must be a positive integer")


def _validate_timeout(settings: Mapping[str, object]) -> None:
    timeout_seconds = settings["timeout_seconds"]
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise ValueError("timeout_seconds must be finite and positive")


def _validate_identifiers(settings: Mapping[str, object]) -> None:
    resource_revision = settings["resource_revision"]
    if not isinstance(resource_revision, str) or not resource_revision.strip():
        raise ValueError("resource_revision must be non-empty")
    for identifier in ("request_id", "attempt_id", "stage_id"):
        setting_value = settings[identifier]
        if not isinstance(setting_value, str) or not setting_value:
            raise ValueError(f"{identifier} must be non-empty")


def _validate_telemetry(settings: Mapping[str, object]) -> None:
    telemetry = settings["telemetry"]
    if telemetry is not None and not callable(telemetry):
        raise ValueError("telemetry must be callable")


def _validate_boolean_flags(settings: Mapping[str, object]) -> None:
    if not isinstance(settings["local_files_only"], bool):
        raise ValueError("local_files_only must be boolean")
    if not isinstance(settings["fail_closed"], bool):
        raise ValueError("fail_closed must be boolean")


def _validate_score_scale(settings: Mapping[str, object]) -> None:
    score_scale = settings["score_scale"]
    if not isinstance(score_scale, str) or not score_scale.strip():
        raise ValueError("score_scale must be non-empty")


def validate_settings(settings: Mapping[str, object]) -> None:
    """Validate candidate extractor settings without changing them."""
    _validate_positive_settings(
        settings,
        ("max_text_length", "max_candidates", "max_model_calls"),
    )
    _validate_timeout(settings)
    _validate_positive_settings(
        settings,
        ("memory_limit_bytes", "cpu_threads"),
    )
    _validate_identifiers(settings)
    _validate_telemetry(settings)
    _validate_boolean_flags(settings)
    _validate_score_scale(settings)
