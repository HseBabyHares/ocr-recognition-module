"""Stage sequencing helpers for the recognition runtime."""

from __future__ import annotations

from sird_recognition._runtime_models import (
    FormResolution,
    RecognitionResponse,
    RecognizeRequest,
    _ResponseState,
)
from sird_recognition._runtime_request import RecognitionError
from sird_recognition._runtime_response import (
    execution_metadata as _execution_metadata,
)
from sird_recognition._runtime_response import (
    resolve_form_response as _resolve_form_response,
)
from sird_recognition._runtime_response import (
    subject_response as _subject_response,
)
from sird_recognition._runtime_response import (
    success_response as _success_response,
)
from sird_recognition._runtime_status import (
    FormResolutionStatus,
    SubjectDiagnostic,
)
from sird_recognition._runtime_technical import technical_response
from sird_recognition.codes import TechnicalCode
from sird_recognition.contracts.ports import (
    ExecuteProfilePort,
    PreparePort,
    ProbePort,
    ResolvePort,
)
from sird_recognition.contracts.stages import (
    FormResolutionDecision,
    PreparedDocument,
    ProbeResult,
    ResolvedForm,
    StageContext,
)


def request_matches_context(
    request: RecognizeRequest,
    context: StageContext,
) -> bool:
    return (
        request.request_id == context.request_id
        and request.artifact_capability == context.artifact_capability
        and request.policy_ref == context.policy_ref
        and dict(request.limits) == dict(context.limits)
    )


def prepare_and_probe(
    prepare: PreparePort,
    probe_port: ProbePort,
    state: _ResponseState,
) -> tuple[PreparedDocument, ProbeResult] | RecognitionResponse:
    prepared = prepare.prepare(state.context)
    state.prepared = prepared
    state.preparation_diagnostics = prepared.diagnostics
    probe = probe_port.probe(prepared, state.context)
    state.probe = probe
    state.evidence_refs = probe.evidence_refs
    if not probe.analysis_complete:
        return technical_response(
            state,
            RecognitionError(TechnicalCode.EXECUTION_ERROR),
        )
    candidate_count = len(probe.candidate_ids)
    if candidate_count == 0:
        return _subject_response(
            state,
            SubjectDiagnostic.TARGET_NOT_DETECTED,
            FormResolution(FormResolutionStatus.UNRESOLVED),
        )
    if candidate_count > 1:
        return _subject_response(
            state,
            SubjectDiagnostic.MULTIPLE_CANDIDATES,
            FormResolution(FormResolutionStatus.AMBIGUOUS),
        )
    return prepared, probe


def resolve_specification(
    resolve: ResolvePort,
    state: _ResponseState,
) -> None:
    probe = state.probe
    if probe is None:
        raise RecognitionError(TechnicalCode.EXECUTION_ERROR)
    decision: FormResolutionDecision = resolve.resolve(probe, state.context)
    state.resolution = decision
    if isinstance(decision, ResolvedForm):
        state.specification = decision.specification
        return
    state.specification = None


def run_stage_sequence(
    prepare: PreparePort,
    probe: ProbePort,
    resolve: ResolvePort,
    execute_profile: ExecuteProfilePort,
    state: _ResponseState,
) -> RecognitionResponse:
    prepared_or_response = prepare_and_probe(prepare, probe, state)
    if isinstance(prepared_or_response, RecognitionResponse):
        return prepared_or_response
    resolve_specification(resolve, state)
    if state.specification is None:
        return _resolve_form_response(state)
    state.prepared = prepared_or_response[0]
    execution = execute_profile.execute(
        state.prepared,
        state.specification,
        state.context,
        observations=prepared_or_response[1].observations,
    )
    state.execution = execution
    state.execution_diagnostics = execution.diagnostics
    state.execution_metadata = _execution_metadata(
        state.specification, execution
    )
    return _success_response(state)
