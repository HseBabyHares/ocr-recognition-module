from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import grpc
import pytest

from sird_recognition import _runtime_status
from sird_recognition.codes import TechnicalCode
from sird_recognition.contracts import stages
from sird_recognition.grpc_adapter import (
    OcrServiceStub,
    recognize_pb2,
    register_ocr_service,
)
from tests import _grpc_fixtures as fixtures
from tests._grpc_context import AbortError, FakeContext, FakeRuntime


def _success_runtime() -> FakeRuntime:
    return FakeRuntime(fixtures.SUCCESS_RESPONSE)


@dataclass(frozen=True)
class ResponseCase:
    spec: fixtures.ResponseSpec
    operation_status: int
    task_outcome: int
    completeness: int
    technical: int | None


RESPONSE_CASES = (
    ResponseCase(
        fixtures.ResponseSpec(
            _runtime_status.OperationStatus.OK,
            _runtime_status.TaskOutcome.COMPLETED,
            _runtime_status.ResultCompleteness.COMPLETE,
        ),
        recognize_pb2.OPERATION_STATUS_OK,
        recognize_pb2.TASK_OUTCOME_COMPLETED,
        recognize_pb2.RESULT_COMPLETENESS_COMPLETE,
        None,
    ),
    ResponseCase(
        fixtures.ResponseSpec(
            _runtime_status.OperationStatus.PARTIAL,
            _runtime_status.TaskOutcome.COMPLETED,
            _runtime_status.ResultCompleteness.PARTIAL,
        ),
        recognize_pb2.OPERATION_STATUS_PARTIAL,
        recognize_pb2.TASK_OUTCOME_COMPLETED,
        recognize_pb2.RESULT_COMPLETENESS_PARTIAL,
        None,
    ),
    ResponseCase(
        fixtures.ResponseSpec(
            _runtime_status.OperationStatus.OK,
            _runtime_status.TaskOutcome.SUBJECT_REJECTED,
            _runtime_status.ResultCompleteness.NONE,
        ),
        recognize_pb2.OPERATION_STATUS_OK,
        recognize_pb2.TASK_OUTCOME_SUBJECT_REJECTED,
        recognize_pb2.RESULT_COMPLETENESS_NONE,
        None,
    ),
    ResponseCase(
        fixtures.ResponseSpec(
            _runtime_status.OperationStatus.FAILED,
            _runtime_status.TaskOutcome.FAILED,
            _runtime_status.ResultCompleteness.NONE,
            TechnicalCode.EXECUTION_ERROR,
        ),
        recognize_pb2.OPERATION_STATUS_FAILED,
        recognize_pb2.TASK_OUTCOME_FAILED,
        recognize_pb2.RESULT_COMPLETENESS_NONE,
        recognize_pb2.TECHNICAL_CODE_EXECUTION_ERROR,
    ),
)


class TestRequestAdapter:
    def test_request_mapping(self) -> None:
        runtime = _success_runtime()

        mapped_response = fixtures.invoke(runtime)

        assert (
            mapped_response.task_id,
            mapped_response.request_id,
            mapped_response.attempt_id,
        ) == (
            fixtures.TASK_ID,
            fixtures.REQUEST_ID,
            fixtures.ATTEMPT_ID,
        )
        expected_request, expected_context = fixtures.expected_state()
        assert runtime.request == expected_request
        assert runtime.request is not None
        assert runtime.context == expected_context

    def test_registration_unary_call(self) -> None:
        runtime = _success_runtime()
        server = grpc.server(ThreadPoolExecutor(max_workers=1))
        register_ocr_service(server, runtime)
        port = server.add_insecure_port("localhost:0")
        server.start()
        with grpc.insecure_channel(f"localhost:{port}") as channel:
            mapped_response = OcrServiceStub(channel).Recognize(
                fixtures.request(),
                timeout=2,
            )
        server.stop(0)

        assert (
            mapped_response.operation_status
            == recognize_pb2.OPERATION_STATUS_OK
        )
        assert runtime.request is not None

    @pytest.mark.parametrize("nested", [False, True])
    def test_unknown_wire_fields(self, nested: bool) -> None:
        runtime = _success_runtime()
        context = FakeContext()

        with pytest.raises(AbortError) as error:
            fixtures.invoke(
                runtime,
                fixtures.unknown_request(nested=nested),
                context,
            )

        assert error.value.code_value is grpc.StatusCode.INVALID_ARGUMENT


class TestResponseAdapter:
    @pytest.mark.parametrize("case", RESPONSE_CASES)
    def test_response_outcomes(self, case: ResponseCase) -> None:
        runtime = FakeRuntime(fixtures.response(case.spec))

        mapped_response = fixtures.invoke(runtime)

        assert mapped_response.operation_status == case.operation_status
        assert mapped_response.task_outcome == case.task_outcome
        assert mapped_response.result_completeness == case.completeness
        if case.technical is not None:
            assert mapped_response.technical_code == case.technical

    def test_technical_retry_class(self) -> None:
        spec = fixtures.ResponseSpec(
            _runtime_status.OperationStatus.FAILED,
            _runtime_status.TaskOutcome.FAILED,
            _runtime_status.ResultCompleteness.NONE,
            TechnicalCode.EXECUTION_ERROR,
            "reader failed after its bounded attempt",
        )
        runtime = FakeRuntime(fixtures.response(spec))

        mapped_response = fixtures.invoke(runtime)

        assert mapped_response.technical_reason == spec.technical_reason
        assert (
            mapped_response.technical_reason_class
            == recognize_pb2.TECHNICAL_REASON_CLASS_PERMANENT
        )

    def test_field_and_execution_mapping(self) -> None:
        mapped_response = fixtures.invoke(self._field_runtime())

        mapped_field = mapped_response.fields[0]
        assert (
            mapped_field.field_id,
            mapped_field.value,
            tuple(mapped_field.evidence_refs),
            mapped_field.diagnostics[0].code,
            mapped_field.validations[0].reason,
        ) == (
            "full_name",
            "observed",
            ("field-evidence",),
            "field-diagnostic",
            "format_valid",
        )
        assert mapped_response.diagnostics[0].code == "stage-diagnostic"
        execution = mapped_response.execution
        assert (
            execution.elapsed_ms,
            execution.model_calls,
            execution.cache_hit,
        ) == (4, 1, True)

    def _field_runtime(self) -> FakeRuntime:
        field = stages.FieldResult(
            stages.FieldStatus.EXTRACTED,
            "observed",
            validations=("format_valid",),
            evidence_refs=("field-evidence",),
            diagnostics=("field-diagnostic",),
            required=True,
        )
        return FakeRuntime(
            fixtures.response(
                fixtures.ResponseSpec(
                    _runtime_status.OperationStatus.OK,
                    _runtime_status.TaskOutcome.COMPLETED,
                    _runtime_status.ResultCompleteness.COMPLETE,
                ),
                fields={"full_name": field},
                diagnostics=("stage-diagnostic",),
            ),
        )


class TestRequestFailures:
    def test_bad_contract_version(self) -> None:
        invalid_request = fixtures.request()
        invalid_request.contract_version = "sird.ocr.v2"

        with pytest.raises(AbortError) as error:
            fixtures.invoke(_success_runtime(), invalid_request)

        assert error.value.code_value is grpc.StatusCode.INVALID_ARGUMENT

    def test_runtime_error(self) -> None:
        runtime = FakeRuntime(
            fixtures.SUCCESS_RESPONSE,
            error=RuntimeError("unexpected implementation failure"),
        )

        with pytest.raises(AbortError) as error:
            fixtures.invoke(runtime)

        assert error.value.code_value is grpc.StatusCode.INTERNAL

    def test_deadline_clamps_timeout(self) -> None:
        runtime = _success_runtime()
        context = FakeContext(remaining=fixtures.DEADLINE_REMAINING)

        fixtures.invoke(runtime, context=context)

        assert runtime.request is not None and runtime.context is not None
        assert runtime.request.limits["timeout_seconds"] == min(
            fixtures.REQUEST_TIMEOUT_SECONDS,
            fixtures.DEADLINE_REMAINING,
        )
        assert runtime.context.limits["timeout_seconds"] == min(
            fixtures.REQUEST_TIMEOUT_SECONDS,
            fixtures.DEADLINE_REMAINING,
        )

    def test_invalid_request(self) -> None:
        invalid_request = fixtures.request()
        invalid_request.task_id = ""

        with pytest.raises(AbortError) as error:
            fixtures.invoke(_success_runtime(), invalid_request)

        assert error.value.code_value is grpc.StatusCode.INVALID_ARGUMENT

    def test_inactive_context(self) -> None:
        runtime = _success_runtime()
        context = FakeContext(active=False)

        with pytest.raises(AbortError) as error:
            fixtures.invoke(runtime, context=context)

        assert error.value.code_value is grpc.StatusCode.CANCELLED
        assert runtime.request is None

    def test_expired_deadline(self) -> None:
        runtime = _success_runtime()
        context = FakeContext(remaining=0)

        with pytest.raises(AbortError) as error:
            fixtures.invoke(runtime, context=context)

        assert error.value.code_value is grpc.StatusCode.DEADLINE_EXCEEDED
        assert runtime.request is None
