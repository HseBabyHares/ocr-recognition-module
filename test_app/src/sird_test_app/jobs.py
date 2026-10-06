"""In-memory local job lifecycle for the Swagger application."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import uuid4

from sird_recognition.snils_recognition import SnilsRecognitionResult

from sird_test_app._dataclass_fields import (
    _DataclassFieldSpec,
    _inject_dataclass_fields,
)

OCR_TIMEOUT_SECONDS = 35.0


class SnilsJobReader(Protocol):
    """Recognition service used by one local job."""

    def recognize_image(
        self,
        image_bytes: bytes,
        *,
        timeout_seconds: float,
        language: str = "rus+eng",
    ) -> SnilsRecognitionResult:
        """Recognize one image synchronously."""


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class JobSubmission:
    task_id: str
    request_id: str
    status: JobStatus
    created_at: datetime


@dataclass(frozen=True, slots=True)
@_inject_dataclass_fields
class JobState:
    task_id: str
    request_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    _result_field = _DataclassFieldSpec(
        "result",
        SnilsRecognitionResult | None,
        None,
        "updated_at",
    )
    error: str | None = None


@dataclass(slots=True)
@_inject_dataclass_fields
class _MutableJob:
    task_id: str
    request_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    _result_field = _DataclassFieldSpec(
        "result",
        SnilsRecognitionResult | None,
        None,
        "updated_at",
    )
    error: str | None = None


class InMemorySnilsJobService:
    """Run local recognition jobs without Kafka or PostgreSQL."""

    def __init__(self, reader: SnilsJobReader) -> None:
        self._reader = reader
        self._jobs: dict[str, _MutableJob] = {}

    async def submit(self, image_bytes: bytes) -> JobSubmission:
        created_at = datetime.now(UTC)
        task_id = str(uuid4())
        request_id = str(uuid4())
        job = _MutableJob(
            task_id=task_id,
            request_id=request_id,
            status=JobStatus.QUEUED,
            created_at=created_at,
            updated_at=created_at,
        )
        self._jobs[task_id] = job
        asyncio.create_task(self._run(job, image_bytes))
        return JobSubmission(
            task_id=task_id,
            request_id=request_id,
            status=job.status,
            created_at=created_at,
        )

    async def get_status(self, task_id: str) -> JobState:
        return self._snapshot(self._job(task_id))

    async def get_result(self, task_id: str) -> JobState:
        return self._snapshot(self._job(task_id))

    def _snapshot(self, job: _MutableJob) -> JobState:
        return JobState(
            task_id=job.task_id,
            request_id=job.request_id,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at,
            result=job.result,
            error=job.error,
        )

    async def _run(self, job: _MutableJob, image_bytes: bytes) -> None:
        job.status = JobStatus.RUNNING
        job.updated_at = datetime.now(UTC)
        try:
            recognition_result = await asyncio.to_thread(
                self._reader.recognize_image,
                image_bytes,
                timeout_seconds=OCR_TIMEOUT_SECONDS,
                language="rus+eng",
            )
        except Exception as recognition_error:
            job.error = type(recognition_error).__name__
            job.status = JobStatus.FAILED
        else:
            job.result = recognition_result
            job.status = JobStatus.COMPLETED
        finally:
            job.updated_at = datetime.now(UTC)

    def _job(self, task_id: str) -> _MutableJob:
        try:
            return self._jobs[task_id]
        except KeyError as missing_job_error:
            raise KeyError(task_id) from missing_job_error
