"""Explicit form-resolution decisions exchanged by OCR stages."""

from dataclasses import dataclass

from sird_recognition.contracts.prepared import ExecutionSpec

_STAGES_MODULE = "sird_recognition.contracts.stages"


@dataclass(frozen=True, slots=True)
class ResolvedForm:
    """Explicitly selected form and profile execution specification."""

    __module__ = _STAGES_MODULE

    specification: ExecutionSpec


@dataclass(frozen=True, slots=True)
class AmbiguousForm:
    """Multiple form resolutions remain possible."""

    __module__ = _STAGES_MODULE

    alternatives: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UnsupportedForm:
    """The detected form is not supported by this runtime."""

    __module__ = _STAGES_MODULE

    form_id: str | None = None


@dataclass(frozen=True, slots=True)
class UnresolvedForm:
    """The detected form cannot be resolved."""

    __module__ = _STAGES_MODULE


type FormResolutionDecision = (
    ResolvedForm | AmbiguousForm | UnsupportedForm | UnresolvedForm
)
