import asyncio
from dataclasses import dataclass
from unittest.mock import Mock

import pytest

from sird_recognition.codes import TechnicalCode
from sird_recognition.contracts import stages as stage_contracts
from sird_recognition.runtime import (
    FormResolutionStatus,
    OperationStatus,
    RecognitionError,
    RecognizeRequest,
    RecognizerRuntime,
    ResultCompleteness,
    SubjectDiagnostic,
    TaskOutcome,
)

DETECTED = "detected"
CANDIDATE_ID = "candidate-1"


@dataclass(frozen=True)
class RuntimeSetup:
    document: stage_contracts.PreparedDocument | None = None
    specification: stage_contracts.ExecutionSpec | None = None
    execution: stage_contracts.ExecutionResult | None = None
    execute_error: BaseException | None = None
    resolution: stage_contracts.FormResolutionDecision | None = None


class RuntimeFactory:
    @classmethod
    def request_payload(cls) -> dict[str, object]:
        return {
            "task_id": "task-1",
            "request_id": "request-1",
            "artifact_capability": "capability-1",
            "limits": {"max_pages": 1},
            "policy_ref": "policy-1",
        }

    @classmethod
    def context(cls) -> stage_contracts.StageContext:
        return stage_contracts.StageContext(
            contract_version="sird.ocr.v1",
            request_id="request-1",
            attempt_id="attempt-1",
            artifact_capability="capability-1",
            limits={"max_pages": 1},
            policy_ref="policy-1",
        )

    @classmethod
    def document(
        cls, complete: bool = True
    ) -> stage_contracts.PreparedDocument:
        page = stage_contracts.PreparedPage(
            "page-1", "source-1", "prepared", "sha256:page", {}
        )
        return stage_contracts.PreparedDocument(
            (page,), complete, ("prepare-diagnostic",)
        )

    @classmethod
    def specification(cls) -> stage_contracts.ExecutionSpec:
        return stage_contracts.ExecutionSpec(
            "snils_card",
            "snils-default",
            ("extract",),
            {"reader": "sha256:reader"},
            "calibration-1",
        )

    @classmethod
    def resolution(
        cls,
        specification: stage_contracts.ExecutionSpec | None,
        resolution: stage_contracts.FormResolutionDecision | None,
    ) -> stage_contracts.FormResolutionDecision:
        if resolution is not None:
            return resolution
        if specification is not None:
            return stage_contracts.ResolvedForm(specification)
        return stage_contracts.UnresolvedForm()

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
        setup: RuntimeSetup | None = None,
    ) -> tuple[RecognizerRuntime, Mock, Mock]:
        if setup is None:
            setup = RuntimeSetup()
        resolver = RuntimeFactory.stage(
            "resolve",
            RuntimeFactory.resolution(setup.specification, setup.resolution),
        )
        executor = RuntimeFactory.stage("execute", setup.execution)
        if setup.execute_error is not None:
            executor.execute.side_effect = setup.execute_error
        runtime = RecognizerRuntime(
            RuntimeFactory.stage(
                "prepare", setup.document or RuntimeFactory.document()
            ),
            RuntimeFactory.stage("probe", probe),
            resolver,
            executor,
        )
        return runtime, resolver, executor


class TestIngress:
    def test_ingress_rejects_unknown_selectors(self) -> None:
        with pytest.raises(RecognitionError) as unknown:
            RecognizeRequest.from_mapping(
                {
                    **RuntimeFactory.request_payload(),
                    "candidate_id": "c-1",
                }
            )
        assert unknown.value.code is TechnicalCode.INVALID_INPUT

        with pytest.raises(RecognitionError) as reserved:
            RecognizeRequest.from_mapping(
                {
                    **RuntimeFactory.request_payload(),
                    "form_id": "snils_card",
                }
            )
        assert reserved.value.code is TechnicalCode.INVALID_INPUT


class TestRuntimeSuccess:
    def test_resolved_form_preserves_evidence(self) -> None:
        execution = stage_contracts.ExecutionResult(
            {
                "snils": stage_contracts.FieldResult(
                    stage_contracts.FieldStatus.EXTRACTED, "observed"
                ),
                "full_name": stage_contracts.FieldResult(
                    stage_contracts.FieldStatus.EXTRACTED, "Observed Name"
                ),
            },
            ("execution-evidence",),
            ("execution-diagnostic",),
            True,
        )
        runtime, resolver, executor = RuntimeFactory.runtime(
            stage_contracts.ProbeResult(
                DETECTED, True, (CANDIDATE_ID,), ("probe-evidence",)
            ),
            setup=RuntimeSetup(
                specification=RuntimeFactory.specification(),
                execution=execution,
            ),
        )

        response = runtime.recognize(
            RecognizeRequest.from_mapping(RuntimeFactory.request_payload()),
            RuntimeFactory.context(),
        )

        assert (
            response.operation_status,
            response.task_outcome,
            response.result_completeness,
            response.form_resolution.status,
            response.fields,
            response.evidence_refs,
            "prepare-diagnostic" in response.diagnostics,
            "execution-diagnostic" in response.diagnostics,
        ) == (
            OperationStatus.OK,
            TaskOutcome.COMPLETED,
            ResultCompleteness.COMPLETE,
            FormResolutionStatus.RESOLVED,
            execution.fields,
            ("probe-evidence", "execution-evidence"),
            True,
            True,
        )
        assert resolver.resolve.call_count == 1
        assert executor.execute.call_count == 1

    def test_partial_fields_preserve_values(self) -> None:
        execution = stage_contracts.ExecutionResult(
            {
                "snils": stage_contracts.FieldResult(
                    stage_contracts.FieldStatus.EXTRACTED, "observed"
                ),
                "birth_date": stage_contracts.FieldResult(
                    stage_contracts.FieldStatus.UNREADABLE,
                    None,
                    diagnostics=("field_unreadable",),
                ),
            },
            (),
            ("field_unreadable",),
            False,
        )
        runtime, _, _ = RuntimeFactory.runtime(
            stage_contracts.ProbeResult(DETECTED, True, (CANDIDATE_ID,), ()),
            setup=RuntimeSetup(
                specification=RuntimeFactory.specification(),
                execution=execution,
            ),
        )

        response = runtime.recognize(
            RuntimeFactory.request_payload(), RuntimeFactory.context()
        )

        assert response.operation_status is OperationStatus.OK
        assert response.task_outcome is TaskOutcome.COMPLETED
        assert response.result_completeness is ResultCompleteness.PARTIAL
        assert response.fields == execution.fields
        assert "field_unreadable" in response.diagnostics


class TestRuntimeRejections:
    def test_no_candidate_rejects_without_resolution(self) -> None:
        runtime, resolver, executor = RuntimeFactory.runtime(
            stage_contracts.ProbeResult(
                "not_detected", True, (), ("search-evidence",)
            ),
            setup=RuntimeSetup(
                specification=RuntimeFactory.specification(),
                execution=stage_contracts.ExecutionResult({}, (), (), True),
            ),
        )

        response = runtime.recognize(
            RuntimeFactory.request_payload(), RuntimeFactory.context()
        )

        assert (
            response.operation_status,
            response.task_outcome,
            response.result_completeness,
            response.subject_diagnostic,
            resolver.resolve.call_count,
            executor.execute.call_count,
        ) == (
            OperationStatus.OK,
            TaskOutcome.SUBJECT_REJECTED,
            ResultCompleteness.NONE,
            SubjectDiagnostic.TARGET_NOT_DETECTED,
            0,
            0,
        )

    def test_multiple_candidates_reject(self) -> None:
        runtime, resolver, executor = RuntimeFactory.runtime(
            stage_contracts.ProbeResult(
                DETECTED, True, (CANDIDATE_ID, "candidate-2"), ()
            ),
            setup=RuntimeSetup(
                specification=RuntimeFactory.specification(),
                execution=stage_contracts.ExecutionResult(
                    {
                        "unexpected": stage_contracts.FieldResult(
                            stage_contracts.FieldStatus.EXTRACTED, "value"
                        )
                    },
                    (),
                    (),
                    True,
                ),
            ),
        )

        response = runtime.recognize(
            RuntimeFactory.request_payload(), RuntimeFactory.context()
        )

        assert (
            response.subject_diagnostic,
            response.form_resolution.status,
            response.fields,
            resolver.resolve.call_count,
            executor.execute.call_count,
        ) == (
            SubjectDiagnostic.MULTIPLE_CANDIDATES,
            FormResolutionStatus.AMBIGUOUS,
            {},
            0,
            0,
        )

    def test_unsupported_form_rejects(self) -> None:
        runtime, resolver, executor = RuntimeFactory.runtime(
            stage_contracts.ProbeResult(
                DETECTED, True, (CANDIDATE_ID,), ("form-evidence",)
            ),
            setup=RuntimeSetup(
                resolution=stage_contracts.UnsupportedForm("unsupported-form"),
                execution=stage_contracts.ExecutionResult({}, (), (), True),
            ),
        )

        response = runtime.recognize(
            RuntimeFactory.request_payload(), RuntimeFactory.context()
        )

        assert (
            response.subject_diagnostic,
            response.form_resolution.status,
            response.form_resolution.form_id,
            response.task_outcome,
            resolver.resolve.call_count,
            executor.execute.call_count,
        ) == (
            SubjectDiagnostic.FORM_UNSUPPORTED,
            FormResolutionStatus.UNSUPPORTED,
            "unsupported-form",
            TaskOutcome.SUBJECT_REJECTED,
            1,
            0,
        )

    def test_ambiguous_form_rejects_without_execution(self) -> None:
        runtime, resolver, executor = RuntimeFactory.runtime(
            stage_contracts.ProbeResult(
                DETECTED, True, (CANDIDATE_ID,), ("form-evidence",)
            ),
            setup=RuntimeSetup(
                resolution=stage_contracts.AmbiguousForm(("form-a", "form-b")),
                execution=stage_contracts.ExecutionResult({}, (), (), True),
            ),
        )

        response = runtime.recognize(
            RuntimeFactory.request_payload(), RuntimeFactory.context()
        )

        assert response.subject_diagnostic is SubjectDiagnostic.FORM_AMBIGUOUS
        assert (
            response.form_resolution.status is FormResolutionStatus.AMBIGUOUS
        )
        assert response.form_resolution.alternatives == ("form-a", "form-b")
        assert resolver.resolve.call_count == 1
        assert executor.execute.call_count == 0

    def test_unresolved_form_rejects(self) -> None:
        runtime, resolver, executor = RuntimeFactory.runtime(
            stage_contracts.ProbeResult(
                "uncertain", True, (CANDIDATE_ID,), ("form-evidence",)
            ),
            setup=RuntimeSetup(
                resolution=stage_contracts.UnresolvedForm(),
                execution=stage_contracts.ExecutionResult({}, (), (), True),
            ),
        )

        response = runtime.recognize(
            RuntimeFactory.request_payload(), RuntimeFactory.context()
        )

        assert (
            response.subject_diagnostic,
            response.form_resolution.status,
            resolver.resolve.call_count,
            executor.execute.call_count,
        ) == (
            SubjectDiagnostic.FORM_UNRESOLVED,
            FormResolutionStatus.UNRESOLVED,
            1,
            0,
        )


class TestRuntimeFailures:
    def test_technical_failure_and_cancel(self) -> None:
        runtime, _, _ = RuntimeFactory.runtime(
            stage_contracts.ProbeResult(DETECTED, True, (CANDIDATE_ID,), ()),
            setup=RuntimeSetup(
                specification=RuntimeFactory.specification(),
                execute_error=RecognitionError(TechnicalCode.EXECUTION_ERROR),
            ),
        )
        failed = runtime.recognize(
            RuntimeFactory.request_payload(), RuntimeFactory.context()
        )
        assert (
            failed.form_resolution.status,
            failed.operation_status,
            failed.task_outcome,
            failed.result_completeness,
            failed.subject_diagnostic,
        ) == (
            FormResolutionStatus.RESOLVED,
            OperationStatus.FAILED,
            TaskOutcome.FAILED,
            ResultCompleteness.NONE,
            None,
        )

        cancelled_runtime, _, _ = RuntimeFactory.runtime(
            stage_contracts.ProbeResult(DETECTED, True, (CANDIDATE_ID,), ()),
            setup=RuntimeSetup(
                specification=RuntimeFactory.specification(),
                execute_error=asyncio.CancelledError(),
            ),
        )
        cancelled = cancelled_runtime.recognize(
            RuntimeFactory.request_payload(), RuntimeFactory.context()
        )
        assert (
            cancelled.operation_status,
            cancelled.task_outcome,
            cancelled.result_completeness,
            cancelled.subject_diagnostic,
        ) == (
            OperationStatus.CANCELLED,
            TaskOutcome.CANCELLED,
            ResultCompleteness.NONE,
            None,
        )
