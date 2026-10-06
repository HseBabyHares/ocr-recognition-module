"""Shared serialization and response helpers for the HTTP routes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from litestar import Response
from sird_recognition.codes import TechnicalCode
from sird_recognition.runtime import RecognitionError

from sird_test_app.jobs import JobState

HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_REQUEST_TOO_LARGE = 413
HTTP_ACCEPTED = 202
HTTP_OK = 200
HTTP_UNPROCESSABLE_ENTITY = 422
HTTP_INTERNAL_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503
STATUS_FIELD = "status"
DIAGNOSTICS_FIELD = "diagnostics"
TASK_ID_FIELD = "task_id"

REFUSED_STATUS = "refused"
UNAVAILABLE_STATUS = "unavailable"
NOT_FOUND_STATUS = "not_found"

SERVICE_UNAVAILABLE_DIAGNOSTIC = "service_unavailable"
JOB_FAILED_DIAGNOSTIC = "job_failed"

RECOGNITION_TECHNICAL_CODE_FIELD = "technical_code"
MESSAGE_FIELD = "message"

SNILS_NUMBER_FIELD = "snils_number"
FULL_NAME_FIELD = "full_name"
BIRTH_DATE_FIELD = "birth_date"
VARIANT_COUNT_FIELD = "variant_count"
OBSERVATION_COUNT_FIELD = "observation_count"
REQUEST_ID_FIELD = "request_id"
CREATED_AT_FIELD = "created_at"
UPDATED_AT_FIELD = "updated_at"
RESULT_FIELD = "result"


def _json_safe(runtime_value: Any) -> Any:
    """Convert runtime dataclasses and enums to JSON-safe values."""
    if isinstance(runtime_value, Enum):
        return _json_safe(runtime_value.value)
    if is_dataclass(runtime_value) and not isinstance(runtime_value, type):
        return {
            dataclass_field.name: _json_safe(
                getattr(runtime_value, dataclass_field.name)
            )
            for dataclass_field in fields(runtime_value)
        }
    if isinstance(runtime_value, Mapping):
        return {
            str(mapping_key): _json_safe(mapping_value)
            for mapping_key, mapping_value in runtime_value.items()
        }
    if isinstance(runtime_value, (list, tuple, set, frozenset)):
        return [_json_safe(sequence_item) for sequence_item in runtime_value]
    return runtime_value


def _is_invalid_code(technical_code: object) -> bool:
    return str(technical_code).upper() == TechnicalCode.INVALID_INPUT.value


def _invalid_input_response(
    recognition_error: RecognitionError,
) -> Response[Any]:
    return Response(
        content={
            RECOGNITION_TECHNICAL_CODE_FIELD: (
                TechnicalCode.INVALID_INPUT.value
            ),
            MESSAGE_FIELD: str(recognition_error),
        },
        status_code=HTTP_BAD_REQUEST,
    )


def _upload_refusal(
    diagnostics: tuple[str, ...],
    *,
    status_code: int,
) -> Response[Any]:
    return Response(
        content={
            STATUS_FIELD: REFUSED_STATUS,
            SNILS_NUMBER_FIELD: None,
            FULL_NAME_FIELD: None,
            BIRTH_DATE_FIELD: None,
            DIAGNOSTICS_FIELD: list(diagnostics),
            VARIANT_COUNT_FIELD: 0,
            OBSERVATION_COUNT_FIELD: 0,
        },
        status_code=status_code,
    )


def _job_body(
    job_state: JobState,
    *,
    include_result: bool,
) -> dict[str, Any]:
    job_payload: dict[str, Any] = {
        TASK_ID_FIELD: job_state.task_id,
        REQUEST_ID_FIELD: job_state.request_id,
        STATUS_FIELD: job_state.status,
        CREATED_AT_FIELD: job_state.created_at.isoformat(),
        UPDATED_AT_FIELD: job_state.updated_at.isoformat(),
    }
    if job_state.error is not None:
        job_payload[DIAGNOSTICS_FIELD] = [
            JOB_FAILED_DIAGNOSTIC,
            job_state.error,
        ]
    if include_result and job_state.result is not None:
        job_payload[RESULT_FIELD] = _json_safe(job_state.result)
    return job_payload


def _service_unavailable_response() -> Response[Any]:
    return Response(
        content={
            STATUS_FIELD: UNAVAILABLE_STATUS,
            DIAGNOSTICS_FIELD: [SERVICE_UNAVAILABLE_DIAGNOSTIC],
        },
        status_code=HTTP_SERVICE_UNAVAILABLE,
    )


def _task_not_found_response(task_id: str) -> Response[Any]:
    return Response(
        content={STATUS_FIELD: NOT_FOUND_STATUS, TASK_ID_FIELD: task_id},
        status_code=HTTP_NOT_FOUND,
    )
