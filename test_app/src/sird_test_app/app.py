"""Litestar adapter for exercising the stateless recognition runtime."""

from __future__ import annotations

from typing import Any

from litestar import Litestar
from litestar.datastructures import State
from sird_recognition.runtime import RecognizerRuntime

from sird_test_app._app_types import (
    ContextFactory,
    JobServicePort,
    RuntimePort,
)
from sird_test_app._recognition_routes import recognize
from sird_test_app._task_routes import (
    MAX_REQUEST_BYTES,
    _reject_large_request,
    create_task,
    get_task_result,
    get_task_status,
)


def create_app(
    runtime: RecognizerRuntime | RuntimePort,
    context_factory: ContextFactory,
    *,
    job_service: JobServicePort | None = None,
) -> Litestar:
    """Build the runtime boundary and optional asynchronous task routes."""
    handlers: list[Any] = [recognize]
    if job_service is not None:
        handlers.extend([create_task, get_task_status, get_task_result])
    return Litestar(
        route_handlers=handlers,
        state=State(
            {
                "runtime": runtime,
                "context_factory": context_factory,
                "job_service": job_service,
            }
        ),
        before_request=_reject_large_request,
        request_max_body_size=MAX_REQUEST_BYTES,
    )


def create_snils_app(job_service: JobServicePort) -> Litestar:
    """Build the local SNILS task API."""
    return Litestar(
        route_handlers=[create_task, get_task_status, get_task_result],
        state=State({"job_service": job_service}),
        before_request=_reject_large_request,
        request_max_body_size=MAX_REQUEST_BYTES,
    )
