"""Asynchronous SNILS task route handlers."""

from __future__ import annotations

from typing import Any

from litestar import Request, Response, get, post
from litestar.datastructures import State

from sird_test_app import _http_helpers
from sird_test_app._app_types import JobServicePort, SnilsUpload
from sird_test_app._task_response_helpers import result_response
from sird_test_app._upload_helpers import MAX_REQUEST_BYTES, read_upload


def _job_service_from_state(
    request: Request[Any, Any, State],
) -> JobServicePort | None:
    try:
        return request.app.state["job_service"]
    except KeyError:
        return None


def _request_exceeds_limit(request: Request[Any, Any, State]) -> bool:
    content_length = request.headers.get("content-length")
    try:
        is_over_limit = (
            content_length is not None
            and int(content_length) > MAX_REQUEST_BYTES
        )
    except ValueError:
        return False
    return is_over_limit


async def _reject_large_request(
    request: Request[Any, Any, State],
) -> Response[Any] | None:
    if request.url.path == "/tasks" and _request_exceeds_limit(request):
        return _http_helpers._upload_refusal(
            ("image_too_large",),
            status_code=_http_helpers.HTTP_REQUEST_TOO_LARGE,
        )
    return None


@post("/tasks", status_code=_http_helpers.HTTP_ACCEPTED)
async def create_task(
    request: Request[Any, Any, State],
) -> Response[Any]:
    """Create an asynchronous local SNILS recognition job."""
    job_service = _job_service_from_state(request)
    if job_service is None:
        return _http_helpers._service_unavailable_response()
    multipart = await request.form()
    upload_data = SnilsUpload(file=multipart.get("file"))
    image_bytes = await read_upload(upload_data)
    if isinstance(image_bytes, Response):
        return image_bytes
    submission = await job_service.submit(image_bytes)
    return Response(
        content={
            "task_id": submission.task_id,
            "request_id": submission.request_id,
            "status": submission.status,
            "created_at": submission.created_at.isoformat(),
            "status_url": f"/tasks/{submission.task_id}",
            "result_url": f"/tasks/{submission.task_id}/result",
        },
        status_code=_http_helpers.HTTP_ACCEPTED,
    )


@get("/tasks/{task_id:str}")
async def get_task_status(
    task_id: str,
    request: Request[Any, Any, State],
) -> Response[Any]:
    """Return the current status of one local recognition job."""
    job_service = _job_service_from_state(request)
    if job_service is None:
        return _http_helpers._service_unavailable_response()
    try:
        job_state = await job_service.get_status(task_id)
    except KeyError:
        return _http_helpers._task_not_found_response(task_id)
    return Response(
        content=_http_helpers._job_body(job_state, include_result=False),
        status_code=_http_helpers.HTTP_OK,
    )


@get("/tasks/{task_id:str}/result")
async def get_task_result(
    task_id: str,
    request: Request[Any, Any, State],
) -> Response[Any]:
    """Return verified SNILS fields after one job finishes."""
    job_service = _job_service_from_state(request)
    if job_service is None:
        return _http_helpers._service_unavailable_response()
    try:
        job_state = await job_service.get_result(task_id)
    except KeyError:
        return _http_helpers._task_not_found_response(task_id)
    return result_response(job_state)
