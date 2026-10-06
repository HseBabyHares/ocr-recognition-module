"""Executable recognition contract oracles."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sird_verification.adapters import RuntimeAdapter
from sird_verification.contracts import OracleResult, OracleStatus
from sird_verification._oracle_support import blocked, build_result
from sird_verification._recognition_support import (
    candidate_observed,
    has_partial_evidence,
    no_guessing_observed,
    parse_request,
    partial_observed,
    recognize,
)


def strict_selector_rejection_oracle(
    adapter: RuntimeAdapter | None,
    payload: Mapping[str, object] | None,
) -> OracleResult:
    """Prove that undocumented selector keys are rejected at ingress."""
    oracle_id = "recognition.strict-selector-rejection"
    parse_outcome = parse_request(adapter, payload, oracle_id)
    if parse_outcome is not None:
        return parse_outcome
    return build_result(
        oracle_id,
        OracleStatus.FAIL,
        {"rejected": False},
        "strict request parsing accepted an undocumented selector",
    )


def no_candidate_refusal_oracle(
    adapter: RuntimeAdapter | None,
    request: Any | None,
    context: Any | None,
) -> OracleResult:
    """Prove that zero classifier candidates yields subject refusal."""
    oracle_id = "recognition.no-candidate-refusal"
    response, outcome = recognize(adapter, request, context, oracle_id)
    if outcome is not None:
        return outcome
    observed = candidate_observed(
        response,
        "target_not_detected",
        "target_not_detected",
    )
    return _response_result(
        oracle_id,
        observed,
        "zero candidates were refused without a guessed result",
        "zero-candidate refusal contract was not observed",
    )


def multiple_candidate_refusal_oracle(
    adapter: RuntimeAdapter | None,
    request: Any | None,
    context: Any | None,
) -> OracleResult:
    """Prove that multiple classifier candidates are never merged."""
    oracle_id = "recognition.multiple-candidate-refusal"
    response, outcome = recognize(adapter, request, context, oracle_id)
    if outcome is not None:
        return outcome
    observed = candidate_observed(
        response,
        "multiple_candidates",
        "multiple_candidates",
    )
    return _response_result(
        oracle_id,
        observed,
        "multiple candidates were refused without merging",
        "multiple-candidate refusal contract was not observed",
    )


def partial_field_preservation_oracle(
    adapter: RuntimeAdapter | None,
    request: Any | None,
    context: Any | None,
    expected_fields: Mapping[str, object] | None,
) -> OracleResult:
    """Prove that a partial execution preserves returned fields exactly."""
    oracle_id = "recognition.partial-field-preservation"
    if not has_partial_evidence(adapter, request, context, expected_fields):
        return blocked(oracle_id, "required recognition evidence is absent")
    response, outcome = recognize(adapter, request, context, oracle_id)
    if outcome is not None:
        return outcome
    observed = partial_observed(response, expected_fields)
    return _response_result(
        oracle_id,
        observed,
        "partial fields were preserved without replacement",
        "partial field preservation contract was not observed",
    )


def no_guessing_oracle(
    adapter: RuntimeAdapter | None,
    request: Any | None,
    context: Any | None,
) -> OracleResult:
    """Prove that an unresolved form does not produce guessed fields."""
    oracle_id = "recognition.no-guessing"
    response, outcome = recognize(adapter, request, context, oracle_id)
    if outcome is not None:
        return outcome
    observed = no_guessing_observed(response)
    return _response_result(
        oracle_id,
        observed,
        "unresolved form produced no guessed fields",
        "unresolved form produced an unsupported result",
    )


def _response_result(
    oracle_id: str,
    observed: Mapping[str, Any],
    passed_reason: str,
    failed_reason: str,
) -> OracleResult:
    passed = all(observed.values())
    status = OracleStatus.PASS if passed else OracleStatus.FAIL
    reason = passed_reason if passed else failed_reason
    return build_result(oracle_id, status, observed, reason)
