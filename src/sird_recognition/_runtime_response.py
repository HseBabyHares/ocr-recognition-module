"""Subject and successful response construction for the runtime."""

from __future__ import annotations

from collections.abc import Mapping
from typing import NamedTuple, cast

from sird_recognition._runtime_models import (
    FormResolution,
    RecognitionResponse,
    RecognizeRequest,
    _ResponseState,
)
from sird_recognition._runtime_status import (
    FormResolutionStatus,
    OperationStatus,
    ResultCompleteness,
    SubjectDiagnostic,
    TaskOutcome,
)
from sird_recognition.contracts.stages import (
    AmbiguousForm,
    ExecutionResult,
    ExecutionSpec,
    FieldStatus,
    PreparedDocument,
    ProbeResult,
    UnresolvedForm,
    UnsupportedForm,
)

_INCOMPLETE_STATE_MESSAGE = "incomplete recognition response state"
_FIRST_EVIDENCE_INDEX = 0


def resolve_form_response(state: _ResponseState) -> RecognitionResponse:
    decision = state.resolution
    if isinstance(decision, AmbiguousForm):
        return subject_response(
            state,
            SubjectDiagnostic.FORM_AMBIGUOUS,
            FormResolution(
                FormResolutionStatus.AMBIGUOUS,
                alternatives=decision.alternatives,
            ),
        )
    if isinstance(decision, UnsupportedForm):
        return subject_response(
            state,
            SubjectDiagnostic.FORM_UNSUPPORTED,
            FormResolution(
                FormResolutionStatus.UNSUPPORTED,
                form_id=decision.form_id,
            ),
        )
    if isinstance(decision, UnresolvedForm):
        return subject_response(
            state,
            SubjectDiagnostic.FORM_UNRESOLVED,
            FormResolution(FormResolutionStatus.UNRESOLVED),
        )
    raise TypeError("unsupported form-resolution decision")


_RequiredState = NamedTuple(
    "_RequiredState",
    (
        ("request", RecognizeRequest),
        ("prepared", PreparedDocument),
        ("probe", ProbeResult),
        ("specification", ExecutionSpec),
        ("execution", ExecutionResult),
    ),
)


def success_response(state: _ResponseState) -> RecognitionResponse:
    required_state = _required_state(state)
    return RecognitionResponse(
        operation_status=_operation_status(
            required_state.prepared.preparation_complete
        ),
        task_outcome=TaskOutcome.COMPLETED,
        result_completeness=subject_completeness(required_state.execution),
        form_resolution=FormResolution(
            FormResolutionStatus.RESOLVED,
            form_id=required_state.specification.form_id,
            decision_evidence_ref=(
                required_state.probe.evidence_refs[_FIRST_EVIDENCE_INDEX]
                if required_state.probe.evidence_refs
                else None
            ),
        ),
        search_result=required_state.probe.search_result,
        fields=required_state.execution.fields,
        diagnostics=(
            required_state.prepared.diagnostics
            + required_state.execution.diagnostics
        ),
        evidence_refs=(
            required_state.probe.evidence_refs
            + required_state.execution.evidence_refs
        ),
        execution=state.execution_metadata,
        subject_diagnostic=SubjectDiagnostic.SUPPORTED,
        task_id=required_state.request.task_id,
        request_id=required_state.request.request_id,
    )


def _required_state(state: _ResponseState) -> _RequiredState:
    required_values = (
        state.request,
        state.prepared,
        state.probe,
        state.specification,
        state.execution,
    )
    if any(required_value is None for required_value in required_values):
        raise TypeError(_INCOMPLETE_STATE_MESSAGE)
    return _RequiredState(
        *cast(
            tuple[
                RecognizeRequest,
                PreparedDocument,
                ProbeResult,
                ExecutionSpec,
                ExecutionResult,
            ],
            required_values,
        )
    )


def subject_completeness(execution: ExecutionResult) -> ResultCompleteness:
    """Derive subject completeness only from explicit field outcomes."""
    if not execution.complete or not execution.fields:
        return ResultCompleteness.PARTIAL
    required_fields = (
        field_result
        for field_result in execution.fields.values()
        if field_result.required
    )
    if any(
        field_result.status is not FieldStatus.EXTRACTED
        for field_result in required_fields
    ):
        return ResultCompleteness.PARTIAL
    return ResultCompleteness.COMPLETE


def execution_metadata(
    specification: ExecutionSpec | None,
    execution: ExecutionResult | None = None,
) -> Mapping[str, object]:
    if specification is None:
        return {}
    metadata: dict[str, object] = {
        "form_id": specification.form_id,
        "profile_id": specification.profile_id,
        "stage_names": specification.stage_names,
        "implementation_checksums": specification.implementation_checksums,
        "calibration_ref": specification.calibration_ref,
    }
    if execution is not None and execution.execution_metadata:
        metadata["profile_execution"] = dict(execution.execution_metadata)
    return metadata


def subject_response(
    state: _ResponseState,
    subject: SubjectDiagnostic,
    form_resolution: FormResolution,
) -> RecognitionResponse:
    request = state.request
    probe = state.probe
    if request is None or probe is None:
        raise TypeError("incomplete subject response state")
    return RecognitionResponse(
        operation_status=OperationStatus.OK,
        task_outcome=TaskOutcome.SUBJECT_REJECTED,
        result_completeness=ResultCompleteness.NONE,
        form_resolution=form_resolution,
        search_result=probe.search_result,
        fields={},
        diagnostics=state.preparation_diagnostics + (subject.value,),
        evidence_refs=state.evidence_refs,
        execution=state.execution_metadata,
        subject_diagnostic=subject,
        task_id=request.task_id,
        request_id=request.request_id,
    )


def _operation_status(preparation_complete: bool) -> OperationStatus:
    if preparation_complete:
        return OperationStatus.OK
    return OperationStatus.PARTIAL
