"""Public value and protocol contracts for candidate extraction."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from sird_recognition.contracts.text_observation import (
    TextObservation,
    TextRegion,
)

_CANDIDATE_MODULE = "sird_recognition.candidate_extraction"


class CandidateField(StrEnum):
    """Supported field hypotheses emitted by a candidate model."""

    __module__ = _CANDIDATE_MODULE

    FULL_NAME = "full_name"
    BIRTH_DATE = "birth_date"
    BIRTH_PLACE = "birth_place"
    REGISTRATION_DATE = "registration_date"


@dataclass(frozen=True, slots=True)
class CandidateSpan:
    """One model proposal, retaining raw score and source provenance."""

    __module__ = _CANDIDATE_MODULE

    field: CandidateField
    raw_text: str
    start: int
    end: int
    score: float
    score_scale: str
    observation_id: str
    model_id: str
    model_revision: str
    region: TextRegion | None = None

    def __post_init__(self) -> None:
        self._validate_raw_text()
        self._validate_offsets()
        self._validate_score()

    @property
    def raw_score(self) -> float:
        """Return the uncalibrated model score without changing its scale."""
        return self.score

    def _validate_raw_text(self) -> None:
        if not self.raw_text:
            raise ValueError("raw_text must be non-empty")

    def _validate_offsets(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError("candidate offsets are invalid")

    def _validate_score(self) -> None:
        if not isinstance(self.score, (int, float)) or isinstance(
            self.score,
            bool,
        ):
            raise ValueError("score must be numeric")
        if not self.score_scale:
            raise ValueError("score_scale must be non-empty")


class CandidateExtractionError(RuntimeError):
    """Base error for the optional candidate stage."""

    __module__ = _CANDIDATE_MODULE


class CandidateStageUnavailableError(CandidateExtractionError):
    """The candidate model or its tokenizer cannot be used."""

    __module__ = _CANDIDATE_MODULE


class CandidateStageLimitError(CandidateStageUnavailableError):
    """The candidate stage cannot satisfy a configured resource limit."""

    __module__ = _CANDIDATE_MODULE


@dataclass(frozen=True, slots=True)
class CandidateStageTelemetry:
    """Safe candidate-stage event without document content."""

    __module__ = _CANDIDATE_MODULE

    request_id: str
    attempt_id: str
    stage_id: str
    event: str
    model_id: str | None
    model_revision: str | None
    resource_revision: str
    elapsed_seconds: float
    candidate_count: int
    limit_state: str
    reason_code: str


CandidateTelemetrySink = Callable[[CandidateStageTelemetry], None]


@runtime_checkable
class CandidateExtractor(Protocol):
    """Extract evidence-only spans from one OCR observation."""

    __module__ = _CANDIDATE_MODULE

    def extract(
        self, observation: TextObservation
    ) -> tuple[CandidateSpan, ...]:
        """Return candidate spans, without selecting a field value."""
