"""Preparation and classifier records exchanged by OCR stages."""

from collections.abc import Mapping
from dataclasses import dataclass, field

_STAGES_MODULE = "sird_recognition.contracts.stages"


@dataclass(frozen=True, slots=True)
class StageContext:
    """Request-scoped inputs passed explicitly to every stage."""

    __module__ = _STAGES_MODULE

    contract_version: str
    request_id: str
    attempt_id: str
    artifact_capability: str
    limits: Mapping[str, int | float]
    policy_ref: str


@dataclass(frozen=True, slots=True)
class PreparedPage:
    """Prepared page with source and artifact provenance."""

    __module__ = _STAGES_MODULE

    page_id: str
    source_id: str
    status: str
    checksum: str
    metadata: Mapping[str, object]
    prepared_artifact: str | None = None
    page_index: int | None = None


@dataclass(frozen=True, slots=True)
class PreparedDocument:
    """Preparation result with explicit completeness."""

    __module__ = _STAGES_MODULE

    pages: tuple[PreparedPage, ...]
    preparation_complete: bool
    diagnostics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Classifier probe result before form/profile execution."""

    __module__ = _STAGES_MODULE

    search_result: str
    analysis_complete: bool
    candidate_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExecutionSpec:
    """Classifier-resolved profile execution specification."""

    __module__ = _STAGES_MODULE

    form_id: str
    profile_id: str
    stage_names: tuple[str, ...]
    implementation_checksums: Mapping[str, str]
    calibration_ref: str
    reader_language: str | None = None
    reader_cpu_threads: int = 1
    reader_order: tuple[str, ...] = ()
    reader_model_revisions: Mapping[str, str] = field(default_factory=dict)
