"""Status values used by the recognition runtime."""

from enum import StrEnum


class OperationStatus(StrEnum):
    """Technical status of one bounded recognition call."""

    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"
    LIMIT_EXCEEDED = "limit_exceeded"


class TaskOutcome(StrEnum):
    """Terminal subject or technical outcome, when known by this attempt."""

    COMPLETED = "completed"
    SUBJECT_REJECTED = "subject_rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"
    LIMIT_EXCEEDED = "limit_exceeded"


class ResultCompleteness(StrEnum):
    """Completeness of the subject result, independent of transport status."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    NONE = "none"


class FormResolutionStatus(StrEnum):
    """Classifier resolution state for the selected document form."""

    UNSPECIFIED = "unspecified"
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"
    UNSUPPORTED = "unsupported"


class SubjectDiagnostic(StrEnum):
    """Stable subject-level diagnostics returned by the computation stage."""

    SUPPORTED = "supported"
    TARGET_NOT_DETECTED = "target_not_detected"
    FORM_AMBIGUOUS = "form_ambiguous"
    FORM_UNSUPPORTED = "form_unsupported"
    FORM_UNRESOLVED = "form_unresolved"
    MULTIPLE_CANDIDATES = "multiple_candidates"
