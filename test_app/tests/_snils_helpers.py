"""SNILS-specific helpers for HTTP adapter tests."""

import time
from importlib import import_module
from typing import Any

from litestar.testing import TestClient
from sird_recognition.runtime import RecognizeRequest
from sird_recognition.snils_recognition import (
    SnilsRecognitionResult,
    SnilsRecognitionStatus,
)

_test_helpers = import_module("_test_helpers")


def snils_result(recognition_status: str) -> SnilsRecognitionResult:
    is_verified = (
        recognition_status == _test_helpers.TEST_CONSTANTS["verified_status"]
    )
    return SnilsRecognitionResult(
        status=(
            SnilsRecognitionStatus.VERIFIED
            if is_verified
            else SnilsRecognitionStatus.REFUSED
        ),
        snils_number="11223344595" if is_verified else None,
        full_name="Example Person" if is_verified else None,
        birth_date="1990-02-01" if is_verified else None,
        diagnostics=(
            ("snils_checksum_valid",) if is_verified else ("unreadable",)
        ),
        variant_count=4,
        observation_count=4,
    )


def submit_snils_task(client: TestClient) -> str:
    created_response = client.post(
        "/tasks",
        files={"file": ("snils.png", b"image-bytes", "image/png")},
    )
    task_id = created_response.json()["task_id"]
    assert (
        created_response.status_code
        == _test_helpers.TEST_CONSTANTS["accepted_status_code"]
    )
    assert created_response.json()["status"] == "queued"

    status_response = client.get(f"/tasks/{task_id}")
    assert (
        status_response.status_code
        == _test_helpers.TEST_CONSTANTS["ok_status_code"]
    )
    assert status_response.json()["task_id"] == task_id
    return task_id


def poll_task_result(client: TestClient, task_id: str) -> Any:
    for _ in range(_test_helpers.TEST_CONSTANTS["max_result_polls"]):
        result_response = client.get(f"/tasks/{task_id}/result")
        if (
            result_response.status_code
            != _test_helpers.TEST_CONSTANTS["accepted_status_code"]
        ):
            return result_response
        time.sleep(_test_helpers.TEST_CONSTANTS["poll_interval_seconds"])
    return result_response


def assert_valid_response(http_response: Any, runtime_spy: Any) -> None:
    assert (
        http_response.status_code
        == _test_helpers.TEST_CONSTANTS["created_status_code"]
    )
    assert http_response.json()["fields"] == {
        "snils": {
            "status": "extracted",
            "field_value": "observed",
            "validations": ["format_valid"],
            "evidence_refs": ["evidence-1"],
            "diagnostics": [],
            "required": True,
        },
        "birth_date": {
            "status": "unreadable",
            "field_value": None,
            "validations": [],
            "evidence_refs": [],
            "diagnostics": ["field_unreadable"],
            "required": True,
        },
    }
    assert "field_results" not in http_response.json()
    assert runtime_spy.recognize_calls[0][0] == RecognizeRequest.from_mapping(
        _test_helpers.request_payload()
    )
    assert runtime_spy.recognize_calls[0][1] is _test_helpers.CONTEXT


def assert_task_result(result_response: Any, service: Any) -> None:
    assert (
        result_response.status_code
        == _test_helpers.TEST_CONSTANTS["ok_status_code"]
    )
    assert result_response.json()["result"]["snils_number"] == "11223344595"
    assert service.image_calls == [b"image-bytes"]
