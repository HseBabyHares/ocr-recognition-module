"""Private contracts shared by the Litestar route modules."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from litestar.datastructures import UploadFile
from sird_recognition.contracts.stages import StageContext
from sird_recognition.runtime import RecognizeRequest

from sird_test_app._dataclass_fields import (
    _DataclassFieldSpec,
    _inject_dataclass_fields,
)
from sird_test_app.jobs import JobState, JobSubmission

ContextFactory = Callable[[RecognizeRequest], StageContext]


@dataclass
@_inject_dataclass_fields
class SnilsUpload:
    """Multipart upload containing the SNILS image in ``file``."""

    _file_field = _DataclassFieldSpec("file", UploadFile | None, None)


class JobServicePort(Protocol):
    """Local asynchronous job lifecycle used by the HTTP boundary."""

    async def submit(self, image_bytes: bytes) -> JobSubmission:
        """Queue one image for recognition."""

    async def get_status(self, task_id: str) -> JobState:
        """Return current job state."""

    async def get_result(self, task_id: str) -> JobState:
        """Return current job state and result."""


class RuntimePort(Protocol):
    """The runtime method used by the HTTP boundary."""

    def recognize(
        self, request: RecognizeRequest, context: StageContext
    ) -> object:
        """Run one strict request without owning durable task state."""
