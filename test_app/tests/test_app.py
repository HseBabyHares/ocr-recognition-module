"""HTTP adapter behavior tests."""

from importlib import import_module
from typing import Any, cast

from litestar.testing import TestClient
from sird_recognition.runtime import (
    FormResolution,
    FormResolutionStatus,
    OperationStatus,
    RecognitionResponse,
)

from sird_test_app import create_app, create_snils_app
from sird_test_app.jobs import InMemorySnilsJobService

snils_helpers = import_module("_snils_helpers")
helpers = import_module("_test_helpers")


def test_valid_request_serializes_result() -> None:
    recognition_response = helpers.valid_recognition_response()
    runtime_spy = helpers.RuntimeSpy(recognition_response, [])

    with TestClient(
        create_app(runtime_spy, helpers.context_for_request),
    ) as client:
        http_response = client.post(
            "/recognize", json=helpers.request_payload()
        )

    snils_helpers.assert_valid_response(http_response, runtime_spy)


def test_selector_rejected() -> None:
    runtime_spy = helpers.RuntimeSpy(
        recognition_result=None, recognize_calls=[]
    )

    with TestClient(
        create_app(runtime_spy, helpers.context_for_request),
    ) as client:
        http_response = client.post(
            "/recognize",
            json={**helpers.request_payload(), "form_id": "snils_card"},
        )

    assert (
        http_response.status_code
        == helpers.TEST_CONSTANTS["bad_request_status_code"]
    )
    assert http_response.json()["technical_code"] == "INVALID_INPUT"
    assert len(runtime_spy.recognize_calls) == 0


def test_invalid_input_maps_bad_request() -> None:
    recognition_response = RecognitionResponse(
        operation_status=OperationStatus.FAILED,
        task_outcome=None,
        result_completeness=None,
        form_resolution=FormResolution(FormResolutionStatus.UNSPECIFIED),
        search_result=None,
        fields={},
        diagnostics=(),
        evidence_refs=(),
        technical_code="INVALID_INPUT",
    )
    runtime_spy = helpers.RuntimeSpy(recognition_response, [])

    with TestClient(
        create_app(runtime_spy, helpers.context_for_request),
    ) as client:
        http_response = client.post(
            "/recognize", json=helpers.request_payload()
        )

    assert (
        http_response.status_code
        == helpers.TEST_CONSTANTS["bad_request_status_code"]
    )
    assert http_response.json()["technical_code"] == "INVALID_INPUT"


def test_task_routes_create_status_and_result() -> None:
    service = helpers.SnilsServiceSpy(
        snils_helpers.snils_result(
            str(helpers.TEST_CONSTANTS["verified_status"]),
        ),
        [],
    )
    jobs = InMemorySnilsJobService(cast(Any, service))

    with TestClient(create_snils_app(jobs)) as client:
        task_id = snils_helpers.submit_snils_task(client)
        result_response = snils_helpers.poll_task_result(client, task_id)

    snils_helpers.assert_task_result(result_response, service)
