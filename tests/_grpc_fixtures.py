from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sird_recognition import _runtime_models, _runtime_status
from sird_recognition.codes import TechnicalCode
from sird_recognition.contracts import stages
from sird_recognition.grpc_adapter import OcrServiceServicer, recognize_pb2
from tests._grpc_context import FakeContext, FakeRuntime

TASK_ID = "task-1"
REQUEST_ID = "request-1"
ATTEMPT_ID = "attempt-1"
CAPABILITY = "capability-1"
POLICY_ID = "policy-1"
POLICY_VERSION = "v1"
CLASSIFIER_ID = "classifier-1"
CONTRACT_VERSION = "sird.ocr.v1"
DEFAULT_REMAINING = 10.0
REQUEST_TIMEOUT_SECONDS = 1.0
DEADLINE_REMAINING = 0.25


@dataclass(frozen=True)
class ResponseSpec:
    operation: _runtime_status.OperationStatus
    outcome: _runtime_status.TaskOutcome | None
    completeness: _runtime_status.ResultCompleteness | None
    technical_code: TechnicalCode | None = None
    technical_reason: str | None = None


def request() -> recognize_pb2.RecognizeRequest:
    return recognize_pb2.RecognizeRequest(
        contract_version=CONTRACT_VERSION,
        task_id=TASK_ID,
        request_id=REQUEST_ID,
        attempt_id=ATTEMPT_ID,
        artifact_ref=recognize_pb2.ArtifactRef(
            capability=CAPABILITY,
            task_id=TASK_ID,
            request_id=REQUEST_ID,
        ),
        processing_policy=recognize_pb2.ProcessingPolicy(
            input_policy_id=POLICY_ID,
            input_policy_version=POLICY_VERSION,
            classifier_policy_id=CLASSIFIER_ID,
            classifier_policy_version=POLICY_VERSION,
            limits=recognize_pb2.ExecutionLimits(
                timeout_ms=1_000,
                memory_limit_bytes=1,
                max_input_bytes=1,
                max_input_pixels=1,
                max_total_pixels=1,
                max_output_pixels=1,
                max_pages=1,
                cpu_threads=1,
            ),
        ),
    )


def response(
    spec: ResponseSpec,
    *,
    fields: Mapping[str, stages.FieldResult] | None = None,
    diagnostics: tuple[str, ...] = (),
) -> _runtime_models.RecognitionResponse:
    return _runtime_models.RecognitionResponse(
        operation_status=spec.operation,
        task_outcome=spec.outcome,
        result_completeness=spec.completeness,
        form_resolution=_runtime_models.FormResolution(
            _runtime_status.FormResolutionStatus.RESOLVED,
            form_id="snils_card",
            calibration_ref="calibration-1",
            decision_evidence_ref="evidence-1",
        ),
        search_result=None,
        evidence_refs=(),
        fields=fields or {},
        diagnostics=diagnostics,
        execution={"elapsed_ms": 4, "model_calls": 1, "cache_hit": True},
        technical_code=spec.technical_code,
        technical_reason=spec.technical_reason,
    )


def unknown_request(
    *,
    nested: bool = False,
) -> recognize_pb2.RecognizeRequest:
    request_message = request()
    if nested:
        artifact = recognize_pb2.ArtifactRef.FromString(
            b"".join(
                (
                    request_message.artifact_ref.SerializeToString(),
                    b"\x98\x06\x01",
                ),
            ),
        )
        request_message.artifact_ref.CopyFrom(artifact)
        return request_message
    return recognize_pb2.RecognizeRequest.FromString(
        b"".join(
            (
                request_message.SerializeToString(),
                b"\x38\x01",
            ),
        ),
    )


def invoke(
    runtime: FakeRuntime,
    request_message: recognize_pb2.RecognizeRequest | None = None,
    context: FakeContext | None = None,
) -> recognize_pb2.RecognizeResponse:
    selected_request = (
        request() if request_message is None else request_message
    )
    selected_context = (
        FakeContext(remaining=DEFAULT_REMAINING)
        if context is None
        else context
    )
    return OcrServiceServicer(runtime).Recognize(
        selected_request,
        selected_context,
    )


def expected_state() -> tuple[
    _runtime_models.RecognizeRequest,
    stages.StageContext,
]:
    domain_request = _runtime_models.RecognizeRequest(
        task_id=TASK_ID,
        request_id=REQUEST_ID,
        artifact_capability=CAPABILITY,
        limits={
            "timeout_seconds": 1.0,
            "memory_limit_bytes": 1,
            "max_input_bytes": 1,
            "max_input_pixels": 1,
            "max_total_pixels": 1,
            "max_output_pixels": 1,
            "max_pages": 1,
            "cpu_threads": 1,
            "max_model_calls": 0,
            "max_variants": 0,
        },
        policy_ref=POLICY_ID,
    )
    stage_context = stages.StageContext(
        contract_version=CONTRACT_VERSION,
        request_id=REQUEST_ID,
        attempt_id=ATTEMPT_ID,
        artifact_capability=CAPABILITY,
        limits=domain_request.limits,
        policy_ref=POLICY_ID,
    )
    return domain_request, stage_context


SUCCESS_RESPONSE = response(
    ResponseSpec(
        _runtime_status.OperationStatus.OK,
        _runtime_status.TaskOutcome.COMPLETED,
        _runtime_status.ResultCompleteness.COMPLETE,
    ),
)
