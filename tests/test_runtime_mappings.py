import asyncio
from unittest.mock import Mock

import pytest

from sird_recognition.codes import TechnicalCode
from sird_recognition.contracts import stages as stage_contracts
from sird_recognition.runtime import (
    FormResolutionStatus,
    OperationStatus,
    RecognitionError,
    RecognizerRuntime,
    ResultCompleteness,
    SubjectDiagnostic,
    TaskOutcome,
)

PROBE_EVIDENCE = "probe-evidence"


class RuntimeMappingFactory:
    @classmethod
    def request_payload(cls) -> dict[str, object]:
        return {
            "task_id": "task-mapping",
            "request_id": "request-mapping",
            "artifact_capability": "capability-mapping",
            "limits": {"max_pages": 1},
            "policy_ref": "policy-mapping",
        }

    @classmethod
    def context(cls) -> stage_contracts.StageContext:
        return stage_contracts.StageContext(
            contract_version="sird.ocr.v1",
            request_id="request-mapping",
            attempt_id="attempt-mapping",
            artifact_capability="capability-mapping",
            limits={"max_pages": 1},
            policy_ref="policy-mapping",
        )

    @classmethod
    def document(
        cls, *, complete: bool = True
    ) -> stage_contracts.PreparedDocument:
        page = stage_contracts.PreparedPage(
            "page-mapping",
            "source-mapping",
            "prepared",
            "sha256:synthetic",
            {},
        )
        return stage_contracts.PreparedDocument(
            (page,), complete, ("synthetic-prepare",)
        )

    @classmethod
    def specification(cls) -> stage_contracts.ExecutionSpec:
        return stage_contracts.ExecutionSpec(
            "synthetic-form",
            "synthetic-profile",
            ("extract",),
            {"reader": "sha256:synthetic"},
            "calibration-mapping",
        )

    @classmethod
    def stage(cls, method_name: str, stage_result: object) -> Mock:
        stage_mock = Mock()
        getattr(stage_mock, method_name).return_value = stage_result
        return stage_mock

    @classmethod
    def runtime(
        cls,
        probe: stage_contracts.ProbeResult,
        *,
        specification: stage_contracts.ExecutionSpec | None = None,
        execute_error: BaseException | None = None,
        document: stage_contracts.PreparedDocument | None = None,
        decision: stage_contracts.FormResolutionDecision | None = None,
    ) -> tuple[RecognizerRuntime, Mock, Mock]:
        if decision is None:
            if specification is None:
                decision = stage_contracts.UnresolvedForm()
            else:
                decision = stage_contracts.ResolvedForm(specification)
        resolver = RuntimeMappingFactory.stage("resolve", decision)
        executor = RuntimeMappingFactory.stage(
            "execute", stage_contracts.ExecutionResult({}, (), (), True)
        )
        if execute_error is not None:
            executor.execute.side_effect = execute_error
        runtime = RecognizerRuntime(
            RuntimeMappingFactory.stage(
                "prepare",
                document or RuntimeMappingFactory.document(),
            ),
            RuntimeMappingFactory.stage("probe", probe),
            resolver,
            executor,
        )
        return runtime, resolver, executor


class TestRuntimeMappings:
    def test_incomplete_probe_fails_technically(self) -> None:
        runtime, resolver, executor = RuntimeMappingFactory.runtime(
            stage_contracts.ProbeResult(
                "incomplete", False, (), (PROBE_EVIDENCE,)
            ),
            specification=RuntimeMappingFactory.specification(),
        )

        response = runtime.recognize(
            RuntimeMappingFactory.request_payload(),
            RuntimeMappingFactory.context(),
        )

        assert (
            response.operation_status,
            response.task_outcome,
            response.result_completeness,
            response.technical_code,
            response.form_resolution.status,
            response.evidence_refs,
            response.subject_diagnostic,
            resolver.resolve.call_count,
            executor.execute.call_count,
        ) == (
            OperationStatus.FAILED,
            TaskOutcome.FAILED,
            ResultCompleteness.NONE,
            TechnicalCode.EXECUTION_ERROR,
            FormResolutionStatus.UNSPECIFIED,
            (PROBE_EVIDENCE,),
            None,
            0,
            0,
        )

    def test_unresolved_form_rejects(self) -> None:
        runtime, resolver, executor = RuntimeMappingFactory.runtime(
            stage_contracts.ProbeResult(
                "uncertain", True, ("candidate-mapping",), ()
            ),
            specification=None,
        )

        response = runtime.recognize(
            RuntimeMappingFactory.request_payload(),
            RuntimeMappingFactory.context(),
        )

        assert (
            response.operation_status,
            response.task_outcome,
            response.result_completeness,
            response.form_resolution.status,
            response.subject_diagnostic,
            resolver.resolve.call_count,
            executor.execute.call_count,
        ) == (
            OperationStatus.OK,
            TaskOutcome.SUBJECT_REJECTED,
            ResultCompleteness.NONE,
            FormResolutionStatus.UNRESOLVED,
            SubjectDiagnostic.FORM_UNRESOLVED,
            1,
            0,
        )


@pytest.mark.parametrize(
    (
        "raised_error",
        "operation_status",
        "task_outcome",
        "completeness",
        "retryable",
    ),
    [
        (
            RecognitionError(TechnicalCode.EXECUTION_LIMIT_EXCEEDED),
            OperationStatus.LIMIT_EXCEEDED,
            TaskOutcome.LIMIT_EXCEEDED,
            ResultCompleteness.NONE,
            False,
        ),
        (
            RecognitionError(TechnicalCode.CANCELLED),
            OperationStatus.CANCELLED,
            TaskOutcome.CANCELLED,
            ResultCompleteness.NONE,
            False,
        ),
        (
            RecognitionError(TechnicalCode.EXECUTION_ERROR),
            OperationStatus.FAILED,
            TaskOutcome.FAILED,
            ResultCompleteness.NONE,
            False,
        ),
        (
            RecognitionError(TechnicalCode.EXECUTION_ERROR, retryable=True),
            OperationStatus.FAILED,
            None,
            None,
            True,
        ),
    ],
)
def test_execution_errors_are_observable(
    raised_error: RecognitionError,
    operation_status: OperationStatus,
    task_outcome: TaskOutcome | None,
    completeness: ResultCompleteness | None,
    retryable: bool,
) -> None:
    runtime, resolver, executor = RuntimeMappingFactory.runtime(
        stage_contracts.ProbeResult(
            "detected", True, ("candidate-mapping",), (PROBE_EVIDENCE,)
        ),
        specification=RuntimeMappingFactory.specification(),
        execute_error=raised_error,
    )

    response = runtime.recognize(
        RuntimeMappingFactory.request_payload(),
        RuntimeMappingFactory.context(),
    )

    assert (
        response.operation_status,
        response.task_outcome,
        response.result_completeness,
        response.technical_code,
        response.retryable,
        response.form_resolution.status,
        response.form_resolution.form_id,
        response.evidence_refs,
        resolver.resolve.call_count,
        executor.execute.call_count,
    ) == (
        operation_status,
        task_outcome,
        completeness,
        raised_error.code,
        retryable,
        FormResolutionStatus.RESOLVED,
        "synthetic-form",
        (PROBE_EVIDENCE,),
        1,
        1,
    )


class TestRuntimeCancellation:
    def test_async_cancellation_is_terminal(self) -> None:
        runtime, _resolver, executor = RuntimeMappingFactory.runtime(
            stage_contracts.ProbeResult(
                "detected", True, ("candidate-mapping",), ()
            ),
            specification=RuntimeMappingFactory.specification(),
            execute_error=asyncio.CancelledError(),
        )

        response = runtime.recognize(
            RuntimeMappingFactory.request_payload(),
            RuntimeMappingFactory.context(),
        )

        assert (
            response.operation_status,
            response.task_outcome,
            response.result_completeness,
            response.technical_code,
            response.retryable,
            executor.execute.call_count,
        ) == (
            OperationStatus.CANCELLED,
            TaskOutcome.CANCELLED,
            ResultCompleteness.NONE,
            TechnicalCode.CANCELLED,
            False,
            1,
        )
