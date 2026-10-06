"""Small state helpers for bounded OCR invocation."""

from __future__ import annotations

import queue
import time
from dataclasses import dataclass
from typing import Any

from sird_workflow import ocr_outcome as ocr_outcome_module
from sird_workflow.ocr_call_result import OcrCallResult

OcrOutcome = ocr_outcome_module.OcrOutcome


@dataclass(frozen=True, slots=True)
class LocalCancellation:
    payload: OcrCallResult


def _normalized_code(exc: Exception) -> str:
    raw_code = getattr(exc, "code", None)
    code = raw_code() if callable(raw_code) else raw_code
    status_name = getattr(code, "name", None)
    code_text = (
        status_name if isinstance(status_name, str) else str(code or "")
    )
    return code_text.rsplit(".", 1)[-1].upper()


def classify_exception(exc: Exception) -> OcrCallResult:
    normalized = _normalized_code(exc)
    if normalized in {"CANCELLED", "CANCELED"}:
        outcome = OcrOutcome.CANCELLED
    elif (
        normalized in {"UNAVAILABLE", "DEADLINE_EXCEEDED"}
        or getattr(exc, "retryable", False) is True
    ):
        outcome = OcrOutcome.TRANSIENT
    else:
        outcome = OcrOutcome.PERMANENT
    return OcrCallResult(
        outcome=outcome,
        error=f"ocr_call_failed:{type(exc).__name__}",
    )


def cancellation_result(state: Any) -> LocalCancellation | None:
    cancellation = state.cancellation
    if cancellation is None or not cancellation.cancelled:
        return None
    state.executor._cancel()
    outcome = (
        OcrOutcome.CANCELLED if cancellation.terminal else OcrOutcome.TRANSIENT
    )
    return LocalCancellation(
        OcrCallResult(
            outcome,
            error="cancelled",
            requeue=not cancellation.terminal,
        )
    )


def deadline_result(state: Any) -> OcrCallResult | None:
    if state.deadline - time.monotonic() > 0:
        return None
    state.executor._cancel()
    return OcrCallResult(OcrOutcome.TRANSIENT, error="deadline_exceeded")


def read_completed_result(state: Any) -> Any:
    try:
        succeeded, payload, finished_at = state.result_queue.get_nowait()
    except queue.Empty:
        state.executor._cancel()
        return OcrCallResult(OcrOutcome.TRANSIENT, error="deadline_exceeded")
    if finished_at > state.deadline:
        state.executor._cancel()
        return OcrCallResult(OcrOutcome.TRANSIENT, error="deadline_exceeded")
    if succeeded:
        return payload
    raise payload
