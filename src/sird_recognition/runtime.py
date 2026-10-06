"""Stateless orchestration for the production OCR computation boundary.

The runtime owns no task state.  It only validates an ingress request and
composes the transport-neutral stage ports in one bounded call path.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping

from sird_recognition import (
    _runtime_flow,
    _runtime_models,
    _runtime_request,
    _runtime_status,
    _runtime_technical,
)
from sird_recognition.codes import TechnicalCode
from sird_recognition.contracts import ports as _ports
from sird_recognition.contracts import stages as _stages

RecognitionError = _runtime_request.RecognitionError
RecognitionResponse = _runtime_models.RecognitionResponse
RecognizeRequest = _runtime_models.RecognizeRequest
FormResolution = _runtime_models.FormResolution
_ResponseState = _runtime_models._ResponseState

ExecuteProfilePort = _ports.ExecuteProfilePort
PreparePort = _ports.PreparePort
ProbePort = _ports.ProbePort
ResolvePort = _ports.ResolvePort
StageContext = _stages.StageContext

FormResolutionStatus = _runtime_status.FormResolutionStatus
OperationStatus = _runtime_status.OperationStatus
ResultCompleteness = _runtime_status.ResultCompleteness
SubjectDiagnostic = _runtime_status.SubjectDiagnostic
TaskOutcome = _runtime_status.TaskOutcome


class RecognizerRuntime:
    """Compose stateless recognition stages."""

    def __init__(
        self,
        prepare: PreparePort,
        probe: ProbePort,
        resolve: ResolvePort,
        execute_profile: ExecuteProfilePort,
    ) -> None:
        self._prepare = prepare
        self._probe = probe
        self._resolve = resolve
        self._execute_profile = execute_profile

    def recognize(
        self,
        request: RecognizeRequest | Mapping[str, object],
        context: StageContext,
    ) -> RecognitionResponse:
        """Run one bounded stage sequence and map its observable outcome."""
        try:
            parsed_request = (
                request
                if isinstance(request, RecognizeRequest)
                else RecognizeRequest.from_mapping(request)
            )
        except RecognitionError as error:
            return _runtime_technical.technical_response(
                _runtime_models._ResponseState(context=context),
                error,
            )
        state = _runtime_models._ResponseState(
            context=context,
            request=parsed_request,
        )
        if not _runtime_flow.request_matches_context(parsed_request, context):
            return _runtime_technical.technical_response(
                state,
                RecognitionError(TechnicalCode.INVALID_INPUT),
            )
        return self._execute_stages(state)

    def _execute_stages(
        self,
        state: _runtime_models._ResponseState,
    ) -> RecognitionResponse:
        try:
            return _runtime_flow.run_stage_sequence(
                self._prepare,
                self._probe,
                self._resolve,
                self._execute_profile,
                state,
            )
        except RecognitionError as error:
            return _runtime_technical.technical_response(state, error)
        except asyncio.CancelledError:
            return _runtime_technical.technical_response(
                state,
                RecognitionError(TechnicalCode.CANCELLED),
            )
        except Exception:
            # An untyped stage failure is technical, not a subject conclusion.
            return _runtime_technical.technical_response(
                state,
                RecognitionError(TechnicalCode.EXECUTION_ERROR),
            )
