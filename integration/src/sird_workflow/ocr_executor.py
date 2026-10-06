"""Bounded OCR invocation, coercion, cancellation, and error classification."""

from __future__ import annotations

import asyncio
import dataclasses
import queue
import threading
import time
from collections.abc import Mapping
from typing import Any, Protocol, cast

from sird_workflow import (
    _ocr_execution_helpers,
    cancellation,
    ocr_call_result,
    ocr_client,
    ocr_outcome,
    task_event,
)

OCR_DEADLINE_SECONDS = 35.0
OCR_POLL_INTERVAL_SECONDS = 0.05


class _OcrCall(Protocol):
    def __call__(
        self, event: task_event.TaskEvent, *, deadline_seconds: float
    ) -> Any:
        """Invoke one OCR operation."""


def _classify_ocr_exception(
    exc: Exception,
) -> ocr_call_result.OcrCallResult:
    return _ocr_execution_helpers.classify_exception(exc)


@dataclasses.dataclass(slots=True)
class _OcrInvocationState:
    executor: OcrExecutor
    event: task_event.TaskEvent
    cancellation: cancellation.CancellationToken | None
    deadline: float
    result_queue: queue.Queue[tuple[bool, Any, float]]
    completed: threading.Event


def _run_ocr_call(
    invoke: Any,
    event: task_event.TaskEvent,
    result_queue: queue.Queue[tuple[bool, Any, float]],
    completed: threading.Event,
) -> None:
    try:
        call_payload = invoke(event)
    except BaseException as exc:
        result_queue.put((False, exc, time.monotonic()))
    else:
        result_queue.put((True, call_payload, time.monotonic()))
    finally:
        completed.set()


def _wait_for_ocr_call(state: _OcrInvocationState) -> Any:
    while not state.completed.is_set():
        cancellation_result = _ocr_execution_helpers.cancellation_result(state)
        if cancellation_result is not None:
            return cancellation_result
        deadline = _ocr_execution_helpers.deadline_result(state)
        if deadline is not None:
            return deadline
        remaining = state.deadline - time.monotonic()
        state.completed.wait(min(remaining, OCR_POLL_INTERVAL_SECONDS))
    return _ocr_execution_helpers.read_completed_result(state)


class OcrExecutor:
    """Execute one OCR call within a deadline and normalize its outcome."""

    def __init__(self, client: ocr_client.OcrClient) -> None:
        self._client = client

    def execute(
        self,
        event: task_event.TaskEvent,
        cancellation: cancellation.CancellationToken | None = None,
    ) -> ocr_call_result.OcrCallResult:
        try:
            result_value = self._invoke_with_deadline(event, cancellation)
        except asyncio.CancelledError:
            return ocr_call_result.OcrCallResult(
                ocr_outcome.OcrOutcome.CANCELLED, error="cancelled"
            )
        except Exception as exc:
            return _classify_ocr_exception(exc)
        return self._normalize_result(result_value)

    def _normalize_result(
        self, result_value: Any
    ) -> ocr_call_result.OcrCallResult:
        if isinstance(result_value, _ocr_execution_helpers.LocalCancellation):
            return result_value.payload
        return self._coerce(result_value)

    def _invoke(self, event: task_event.TaskEvent) -> Any:
        method = getattr(self._client, "recognize", None)
        if method is None:
            method = getattr(self._client, "process", None)
        if method is None:
            method = getattr(self._client, "call", None)
        if method is None and callable(self._client):
            method = self._client
        if method is None:
            raise TypeError("OCR client has no unary call method")
        call = cast(_OcrCall, method)
        return call(event, deadline_seconds=OCR_DEADLINE_SECONDS)

    def _invoke_with_deadline(
        self,
        event: task_event.TaskEvent,
        cancellation: cancellation.CancellationToken | None,
    ) -> Any:
        deadline = time.monotonic() + OCR_DEADLINE_SECONDS
        result_queue: queue.Queue[tuple[bool, Any, float]] = queue.Queue(
            maxsize=1
        )
        completed = threading.Event()
        state = _OcrInvocationState(
            self, event, cancellation, deadline, result_queue, completed
        )
        thread = threading.Thread(
            target=_run_ocr_call,
            args=(self._invoke, event, result_queue, completed),
            daemon=True,
        )
        thread.start()
        return _wait_for_ocr_call(state)

    def _cancel(self) -> None:
        cancel = getattr(self._client, "cancel", None)
        if not callable(cancel):
            return
        threading.Thread(target=cancel, daemon=True).start()

    def _coerce(
        self, call_value: ocr_call_result.OcrCallResult | Mapping[str, Any]
    ) -> ocr_call_result.OcrCallResult:
        if isinstance(call_value, ocr_call_result.OcrCallResult):
            return dataclasses.replace(call_value, requeue=False)
        if isinstance(call_value, Mapping):
            return ocr_call_result.OcrCallResult(
                outcome=ocr_outcome.OcrOutcome(str(call_value["outcome"])),
                result=call_value.get("result"),
                error=call_value.get("error"),
            )
        raise TypeError("OCR client must return OcrCallResult")
