"""Technical failure response construction for the runtime."""

from __future__ import annotations

from sird_recognition._runtime_models import (
    FormResolution,
    RecognitionResponse,
    _ResponseState,
)
from sird_recognition._runtime_request import RecognitionError
from sird_recognition._runtime_response import execution_metadata
from sird_recognition._runtime_status import (
    FormResolutionStatus,
    OperationStatus,
    ResultCompleteness,
    TaskOutcome,
)
from sird_recognition.codes import TechnicalCode


def technical_status(
    error: RecognitionError,
) -> tuple[OperationStatus, TaskOutcome | None, bool]:
    code_text = str(error.code).upper()
    if code_text == TechnicalCode.CANCELLED.value:
        return OperationStatus.CANCELLED, TaskOutcome.CANCELLED, True
    if code_text in {
        TechnicalCode.INPUT_LIMIT_EXCEEDED.value,
        TechnicalCode.EXECUTION_LIMIT_EXCEEDED.value,
    }:
        return OperationStatus.LIMIT_EXCEEDED, TaskOutcome.LIMIT_EXCEEDED, True
    outcome = None if error.retryable else TaskOutcome.FAILED
    return OperationStatus.FAILED, outcome, error.retryable is False


def technical_form_resolution(state: _ResponseState) -> FormResolution:
    specification = state.specification
    probe = state.probe
    if specification is None:
        return FormResolution(FormResolutionStatus.UNSPECIFIED)
    decision_evidence_ref = None
    if probe is None:
        decision_evidence_ref = None
    elif probe.evidence_refs:
        decision_evidence_ref = probe.evidence_refs[0]
    return FormResolution(
        FormResolutionStatus.RESOLVED,
        form_id=specification.form_id,
        calibration_ref=specification.calibration_ref,
        decision_evidence_ref=decision_evidence_ref,
    )


def technical_response(
    state: _ResponseState,
    error: RecognitionError,
) -> RecognitionResponse:
    operation, outcome, terminal = technical_status(error)
    form_resolution = technical_form_resolution(state)
    return RecognitionResponse(
        operation_status=operation,
        task_outcome=outcome,
        result_completeness=ResultCompleteness.NONE if terminal else None,
        form_resolution=form_resolution,
        search_result=(state.probe.search_result if state.probe else None),
        fields={},
        diagnostics=(
            state.preparation_diagnostics + state.execution_diagnostics
        ),
        evidence_refs=state.evidence_refs,
        execution=_technical_execution(state),
        technical_code=error.code,
        retryable=error.retryable and terminal is False,
        request_id=_request_id(state),
    )


def _technical_execution(state: _ResponseState):
    specification = state.specification
    if specification is None:
        return state.execution_metadata
    return execution_metadata(specification)


def _request_id(state: _ResponseState) -> str:
    request = state.request
    if request is None:
        return state.context.request_id
    return request.request_id
