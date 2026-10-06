from __future__ import annotations

from enum import Enum

from process_tests_setup import make_event, make_service
from sird_workflow.ocr_call_result import OcrCallResult
from sird_workflow.ocr_outcome import OcrOutcome
from sird_workflow.process_outcome import ProcessOutcome
from sird_workflow.task_event import TaskEvent
from sqlalchemy.engine import Engine


class GrpcStatus(Enum):
    UNAVAILABLE = 1
    DEADLINE_EXCEEDED = 2
    RESOURCE_EXHAUSTED = 3
    CANCELLED = 4


class GrpcStyleError(Exception):
    def __init__(self, status: object, *, retryable: bool = False) -> None:
        self._status = status
        self.retryable = retryable

    def code(self) -> object:
        return self._status


class AdapterError(Exception):
    retryable = True

    def code(self) -> str:
        return "ADAPTER_TRANSIENT"


class UntrustedOcr:
    def recognize(
        self, event: TaskEvent, *, deadline_seconds: float
    ) -> OcrCallResult:
        return OcrCallResult(
            OcrOutcome.TRANSIENT,
            error="client_requested_requeue",
            requeue=True,
        )


def run_client_requeue() -> tuple[ProcessOutcome, Engine, TaskEvent]:
    event = make_event()
    service, engine = make_service(event, UntrustedOcr())
    return (
        service.process_event(event, "worker-a", "delivery-a"),
        engine,
        event,
    )
