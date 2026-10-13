"""Shared fixtures and helpers for HTTP adapter tests."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from sird_recognition.contracts.stages import (
    FieldResult,
    FieldStatus,
    StageContext,
)
from sird_recognition.runtime import (
    FormResolution,
    FormResolutionStatus,
    OperationStatus,
    RecognitionResponse,
    RecognizeRequest,
    ResultCompleteness,
)

TEST_CONSTANTS = MappingProxyType(
    {
        "created_status_code": 201,
        "bad_request_status_code": 400,
        "accepted_status_code": 202,
        "ok_status_code": 200,
        "ocr_timeout_seconds": 35.0,
        "ocr_language": "rus+eng",
        "max_result_polls": 20,
        "poll_interval_seconds": 0.01,
        "verified_status": "verified",
    },
)

CONTEXT = StageContext(
    contract_version="sird.ocr.v1",
    request_id="request-1",
    attempt_id="attempt-1",
    artifact_capability="capability-1",
    limits={"max_pages": 1},
    policy_ref="policy-1",
)


def request_payload() -> dict[str, object]:
    return {
        "task_id": "task-1",
        "request_id": "request-1",
        "artifact_capability": "capability-1",
        "limits": {"max_pages": 1},
        "policy_ref": "policy-1",
    }


def context_for_request(_: RecognizeRequest) -> StageContext:
    return CONTEXT


@dataclass
class RuntimeSpy:
    recognition_result: Any
    recognize_calls: list[tuple[RecognizeRequest, StageContext]]

    def recognize(
        self,
        request: RecognizeRequest,
        context: StageContext,
    ) -> Any:
        self.recognize_calls.append((request, context))
        return self.recognition_result


@dataclass
class SnilsServiceSpy:
    recognition_result: Any
    image_calls: list[bytes]

    def recognize_image(
        self,
        image_bytes: bytes,
        *,
        timeout_seconds: float,
        language: str,
        request_id: str | None = None,
    ) -> Any:
        assert request_id
        assert timeout_seconds == TEST_CONSTANTS["ocr_timeout_seconds"]
        assert language == TEST_CONSTANTS["ocr_language"]
        self.image_calls.append(image_bytes)
        return self.recognition_result


def valid_recognition_response() -> RecognitionResponse:
    return RecognitionResponse(
        operation_status=OperationStatus.OK,
        task_outcome=None,
        result_completeness=ResultCompleteness.COMPLETE,
        form_resolution=FormResolution(
            FormResolutionStatus.RESOLVED, "snils_card"
        ),
        search_result="detected",
        fields={
            "snils": FieldResult(
                status=FieldStatus.EXTRACTED,
                value="observed",
                validations=("format_valid",),
                evidence_refs=("evidence-1",),
                diagnostics=(),
            ),
            "birth_date": FieldResult(
                status=FieldStatus.UNREADABLE,
                value=None,
                diagnostics=("field_unreadable",),
            ),
        },
        diagnostics=(),
        evidence_refs=("evidence-1",),
    )
