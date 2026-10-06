"""Injected OCR client boundary."""

from typing import Protocol

from sird_workflow.ocr_call_result import OcrCallResult
from sird_workflow.task_event import TaskEvent


class OcrClient(Protocol):
    """Injected unary OCR boundary. It must honor the supplied deadline."""

    def recognize(
        self, event: TaskEvent, *, deadline_seconds: float
    ) -> OcrCallResult:
        """Run one bounded OCR call."""
