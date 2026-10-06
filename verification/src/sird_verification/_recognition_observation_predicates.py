"""Predicates for recognition response observations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sird_verification._oracle_support import enum_value


def subject_was_rejected(response: Any) -> bool:
    return enum_value(response, "task_outcome") == "subject_rejected"


def diagnostic_matches(response: Any, diagnostic: str) -> bool:
    return enum_value(response, "subject_diagnostic") == diagnostic


def fields_are_empty(response: Any) -> bool:
    return not bool(getattr(response, "fields", None))


def is_partial_response(response: Any) -> bool:
    return enum_value(response, "result_completeness") == "partial"


def fields_match(response: Any, expected_fields: Mapping[str, object]) -> bool:
    observed_fields = dict(getattr(response, "fields", {}))
    return observed_fields == dict(expected_fields)


def form_is_unresolved(response: Any) -> bool:
    resolution = getattr(response, "form_resolution", None)
    return enum_value(resolution, "status") in {"unresolved", "unsupported"}


def form_id_is_missing(response: Any) -> bool:
    resolution = getattr(response, "form_resolution", None)
    return getattr(resolution, "form_id", None) is None
