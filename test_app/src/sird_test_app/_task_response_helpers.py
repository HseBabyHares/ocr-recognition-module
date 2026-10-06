"""Response builders for asynchronous task routes."""

from __future__ import annotations

from litestar import Response

from sird_test_app import _http_helpers
from sird_test_app.jobs import JobState, JobStatus


def result_response(job_state: JobState) -> Response:
    """Map a completed job state to its result response."""
    if job_state.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
        status_code = _http_helpers.HTTP_ACCEPTED
        include_result = False
    elif job_state.status is JobStatus.FAILED:
        status_code = _http_helpers.HTTP_INTERNAL_ERROR
        include_result = False
    else:
        status_code = (
            _http_helpers.HTTP_OK
            if job_state.result and job_state.result.verified
            else _http_helpers.HTTP_UNPROCESSABLE_ENTITY
        )
        include_result = True
    return Response(
        content=_http_helpers._job_body(
            job_state, include_result=include_result
        ),
        status_code=status_code,
    )
