"""Recognition request and runtime invocation support."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

try:
    from sird_recognition.runtime import RecognitionError
except ImportError:
    RecognitionError = None

from sird_verification._oracle_support import blocked, build_result
from sird_verification.adapters import AdapterUnavailableError, RuntimeAdapter
from sird_verification.contracts import OracleResult, OracleStatus

_MISSING_RECOGNITION_EVIDENCE = "required recognition evidence is absent"
_RESPONSE_OBSERVED = "response_observed"
_REJECTED = "rejected"


def has_partial_evidence(
    adapter: RuntimeAdapter | None,
    request: Any | None,
    context: Any | None,
    expected_fields: Mapping[str, object] | None,
) -> bool:
    """Check that partial-field comparison has all required inputs."""
    return all(
        evidence_item is not None
        for evidence_item in (adapter, request, context, expected_fields)
    )


def parse_request(
    adapter: RuntimeAdapter | None,
    payload: Mapping[str, object] | None,
    oracle_id: str,
) -> OracleResult | None:
    """Parse a request and turn parser failures into oracle outcomes."""
    if adapter is None or payload is None:
        return blocked(oracle_id, _MISSING_RECOGNITION_EVIDENCE)
    try:
        adapter.parse_request(payload)
    except AdapterUnavailableError:
        return blocked(oracle_id, "recognition adapter is unavailable")
    except Exception as error:
        return _selector_error(oracle_id, error)
    return None


def recognize(
    adapter: RuntimeAdapter | None,
    request: Any | None,
    context: Any | None,
    oracle_id: str,
) -> tuple[Any, OracleResult | None]:
    """Run recognition and return either its response or an oracle outcome."""
    if adapter is None or request is None or context is None:
        return None, blocked(oracle_id, _MISSING_RECOGNITION_EVIDENCE)
    try:
        response = adapter.recognize(request, context)
    except AdapterUnavailableError:
        return None, blocked(oracle_id, "recognition adapter is unavailable")
    except Exception:
        observed = {_RESPONSE_OBSERVED: False}
        return None, build_result(
            oracle_id,
            OracleStatus.FAIL,
            observed,
            "recognition did not return a response",
        )
    return response, None


def _selector_error(oracle_id: str, error: Exception) -> OracleResult:
    if RecognitionError is None:
        return blocked(oracle_id, "recognition package is unavailable")
    if isinstance(error, RecognitionError):
        observed = {_REJECTED: True}
        return build_result(
            oracle_id,
            OracleStatus.PASS,
            observed,
            "strict request parsing rejected an undocumented selector",
        )
    observed = {_REJECTED: False}
    return build_result(
        oracle_id,
        OracleStatus.FAIL,
        observed,
        "strict request parsing raised an unexpected error",
    )
