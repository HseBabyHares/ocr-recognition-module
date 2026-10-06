"""Recognition response evidence collection support."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sird_verification._recognition_observation_predicates import (
    diagnostic_matches as _diagnostic_matches,
    fields_are_empty as _fields_are_empty,
    fields_match as _fields_match,
    form_id_is_missing as _form_id_is_missing,
    form_is_unresolved as _form_is_unresolved,
    is_partial_response as _is_partial_response,
    subject_was_rejected as _subject_was_rejected,
)

_RESPONSE_OBSERVED = "response_observed"
_SUBJECT_REJECTED = "subject_rejected"
_FIELDS_EMPTY = "fields_empty"


def candidate_observed(
    response: Any,
    diagnostic: str,
    diagnostic_key: str,
) -> dict[str, bool]:
    """Collect refusal and diagnostic evidence from a response."""
    return {
        _RESPONSE_OBSERVED: True,
        _SUBJECT_REJECTED: _subject_was_rejected(response),
        diagnostic_key: _diagnostic_matches(response, diagnostic),
        _FIELDS_EMPTY: _fields_are_empty(response),
    }


def partial_observed(
    response: Any,
    expected_fields: Mapping[str, object],
) -> dict[str, bool]:
    """Collect completeness and exact field-preservation evidence."""
    return {
        _RESPONSE_OBSERVED: True,
        "partial": _is_partial_response(response),
        "fields_preserved": _fields_match(response, expected_fields),
    }


def no_guessing_observed(response: Any) -> dict[str, bool]:
    """Collect evidence that unresolved forms produce no guessed fields."""
    return {
        _RESPONSE_OBSERVED: True,
        _SUBJECT_REJECTED: _subject_was_rejected(response),
        _FIELDS_EMPTY: _fields_are_empty(response),
        "form_unresolved": _form_is_unresolved(response),
        "no_form_id": _form_id_is_missing(response),
    }
