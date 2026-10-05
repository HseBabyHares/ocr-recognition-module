"""Execution result record exchanged by OCR stages."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from sird_recognition.contracts.field_results import FieldResult


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Profile result with typed field and evidence payloads."""

    __module__ = "sird_recognition.contracts.stages"

    fields: Mapping[str, FieldResult]
    evidence_refs: tuple[str, ...]
    diagnostics: tuple[str, ...]
    complete: bool
    execution_metadata: Mapping[str, object] = field(default_factory=dict)
