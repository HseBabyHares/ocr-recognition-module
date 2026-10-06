"""Stateless recognition route handlers."""

from __future__ import annotations

from typing import Any

from litestar import Request, Response, post
from litestar.datastructures import State
from sird_recognition.codes import TechnicalCode
from sird_recognition.runtime import RecognitionError, RecognizeRequest

from sird_test_app._app_types import ContextFactory, RuntimePort
from sird_test_app._http_helpers import (
    HTTP_BAD_REQUEST,
    _invalid_input_response,
    _is_invalid_code,
    _json_safe,
)


async def _parse_request(
    request: Request[Any, Any, State],
) -> RecognizeRequest | Response[Any]:
    try:
        request_payload = await request.json()
    except (RecognitionError, ValueError) as request_json_error:
        return _invalid_input_response(
            _as_recognition_error(request_json_error),
        )
    return _parse_payload(request_payload)


def _parse_payload(
    request_payload: object,
) -> RecognizeRequest | Response[Any]:
    try:
        return RecognizeRequest.from_mapping(request_payload)
    except (RecognitionError, ValueError) as payload_parse_error:
        return _invalid_input_response(
            _as_recognition_error(payload_parse_error),
        )


def _as_recognition_error(
    recognition_parse_error: RecognitionError | ValueError,
) -> RecognitionError:
    if isinstance(recognition_parse_error, RecognitionError):
        return recognition_parse_error
    return RecognitionError(TechnicalCode.INVALID_INPUT)


def _execute_recognition(
    request: Request[Any, Any, State],
    strict_request: RecognizeRequest,
) -> object:
    context_factory: ContextFactory = request.app.state["context_factory"]
    runtime: RuntimePort = request.app.state["runtime"]
    return runtime.recognize(
        strict_request,
        context_factory(strict_request),
    )


@post("/recognize")
async def recognize(request: Request[Any, Any, State]) -> Any:
    """Parse, contextualize, and execute one stateless recognition request."""
    strict_request = await _parse_request(request)
    if isinstance(strict_request, Response):
        return strict_request

    recognition_result = _execute_recognition(request, strict_request)
    technical_code = getattr(recognition_result, "technical_code", None)
    if technical_code is not None and _is_invalid_code(technical_code):
        return Response(
            content=_json_safe(recognition_result),
            status_code=HTTP_BAD_REQUEST,
        )
    return _json_safe(recognition_result)
