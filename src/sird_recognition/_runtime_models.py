"""Data models used by the recognition runtime."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from sird_recognition._runtime_request import (
    RecognizeRequest,
)
from sird_recognition._runtime_status import (
    FormResolutionStatus,
    OperationStatus,
    ResultCompleteness,
    SubjectDiagnostic,
    TaskOutcome,
)
from sird_recognition.codes import TechnicalCode
from sird_recognition.contracts.stages import (
    ExecutionResult,
    ExecutionSpec,
    FieldResult,
    FormResolutionDecision,
    PreparedDocument,
    ProbeResult,
    StageContext,
)


@dataclass(frozen=True, slots=True)
class FormResolution:
    """Form decision and the evidence needed to audit that decision."""

    status: FormResolutionStatus
    form_id: str | None = None
    calibration_ref: str | None = None
    decision_evidence_ref: str | None = None
    alternatives: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RecognitionResponse:
    """Typed result of one bounded stateless recognition computation."""

    operation_status: OperationStatus
    task_outcome: TaskOutcome | None
    result_completeness: ResultCompleteness | None
    form_resolution: FormResolution
    search_result: str | None
    fields: Mapping[str, FieldResult]
    diagnostics: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    execution: Mapping[str, object] = field(default_factory=dict)
    technical_code: TechnicalCode | str | None = None
    technical_reason: str | None = None
    retryable: bool = False
    subject_diagnostic: SubjectDiagnostic | None = None
    task_id: str | None = None
    request_id: str | None = None

    @property
    def execution_metadata(self) -> Mapping[str, object]:
        """Alias matching the stage contract's descriptive terminology."""
        return self.execution


@dataclass(slots=True)
class _ResponseState:
    """Mutable stage state used while constructing a response."""

    context: StageContext
    request: RecognizeRequest | None = None
    prepared: PreparedDocument | None = None
    probe: ProbeResult | None = None
    specification: ExecutionSpec | None = None
    resolution: FormResolutionDecision | None = None
    execution: ExecutionResult | None = None
    preparation_diagnostics: tuple[str, ...] = ()
    execution_diagnostics: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    execution_metadata: Mapping[str, object] = field(default_factory=dict)
