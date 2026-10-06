"""Constants for the protobuf and runtime status contract."""

from __future__ import annotations

from types import MappingProxyType

from sird_recognition import _runtime_status
from sird_recognition._proto.sird.ocr.v1 import recognize_pb2

CONTRACT_VERSION = "sird.ocr.v1"
MILLISECONDS_PER_SECOND = 1000
CALIBRATION_VERSION_KEY = "calibration_version"
LIMIT_FIELDS = (
    "timeout_ms",
    "memory_limit_bytes",
    "max_input_bytes",
    "max_input_pixels",
    "max_total_pixels",
    "max_output_pixels",
    "max_pages",
    "cpu_threads",
    "max_model_calls",
    "max_variants",
)
REQUIRED_LIMIT_FIELDS = LIMIT_FIELDS[:-2]
OPERATION_STATUS = MappingProxyType(
    {
        _runtime_status.OperationStatus.OK.value: (
            recognize_pb2.OPERATION_STATUS_OK
        ),
        _runtime_status.OperationStatus.PARTIAL.value: (
            recognize_pb2.OPERATION_STATUS_PARTIAL
        ),
        _runtime_status.OperationStatus.FAILED.value: (
            recognize_pb2.OPERATION_STATUS_FAILED
        ),
        _runtime_status.OperationStatus.CANCELLED.value: (
            recognize_pb2.OPERATION_STATUS_CANCELLED
        ),
        _runtime_status.OperationStatus.LIMIT_EXCEEDED.value: (
            recognize_pb2.OPERATION_STATUS_LIMIT_EXCEEDED
        ),
    },
)
TASK_OUTCOME = MappingProxyType(
    {
        _runtime_status.TaskOutcome.COMPLETED.value: (
            recognize_pb2.TASK_OUTCOME_COMPLETED
        ),
        _runtime_status.TaskOutcome.SUBJECT_REJECTED.value: (
            recognize_pb2.TASK_OUTCOME_SUBJECT_REJECTED
        ),
        _runtime_status.TaskOutcome.FAILED.value: (
            recognize_pb2.TASK_OUTCOME_FAILED
        ),
        _runtime_status.TaskOutcome.CANCELLED.value: (
            recognize_pb2.TASK_OUTCOME_CANCELLED
        ),
        _runtime_status.TaskOutcome.LIMIT_EXCEEDED.value: (
            recognize_pb2.TASK_OUTCOME_LIMIT_EXCEEDED
        ),
    },
)
RESULT_COMPLETENESS = MappingProxyType(
    {
        _runtime_status.ResultCompleteness.COMPLETE.value: (
            recognize_pb2.RESULT_COMPLETENESS_COMPLETE
        ),
        _runtime_status.ResultCompleteness.PARTIAL.value: (
            recognize_pb2.RESULT_COMPLETENESS_PARTIAL
        ),
        _runtime_status.ResultCompleteness.NONE.value: (
            recognize_pb2.RESULT_COMPLETENESS_NONE
        ),
    },
)
FORM_STATUS = MappingProxyType(
    {
        _runtime_status.FormResolutionStatus.RESOLVED.value: (
            recognize_pb2.FormResolution.RESOLUTION_STATUS_RESOLVED
        ),
        _runtime_status.FormResolutionStatus.AMBIGUOUS.value: (
            recognize_pb2.FormResolution.RESOLUTION_STATUS_AMBIGUOUS
        ),
        _runtime_status.FormResolutionStatus.UNRESOLVED.value: (
            recognize_pb2.FormResolution.RESOLUTION_STATUS_UNRESOLVED
        ),
        _runtime_status.FormResolutionStatus.UNSUPPORTED.value: (
            recognize_pb2.FormResolution.RESOLUTION_STATUS_UNSUPPORTED
        ),
    },
)
SUBJECT_DIAGNOSTIC = MappingProxyType(
    {
        _runtime_status.SubjectDiagnostic.SUPPORTED.value: (
            recognize_pb2.SUBJECT_DIAGNOSTIC_SUPPORTED
        ),
        _runtime_status.SubjectDiagnostic.TARGET_NOT_DETECTED.value: (
            recognize_pb2.SUBJECT_DIAGNOSTIC_TARGET_NOT_DETECTED
        ),
        _runtime_status.SubjectDiagnostic.FORM_AMBIGUOUS.value: (
            recognize_pb2.SUBJECT_DIAGNOSTIC_FORM_AMBIGUOUS
        ),
        _runtime_status.SubjectDiagnostic.FORM_UNSUPPORTED.value: (
            recognize_pb2.SUBJECT_DIAGNOSTIC_FORM_UNSUPPORTED
        ),
        _runtime_status.SubjectDiagnostic.FORM_UNRESOLVED.value: (
            recognize_pb2.SUBJECT_DIAGNOSTIC_FORM_UNRESOLVED
        ),
        _runtime_status.SubjectDiagnostic.MULTIPLE_CANDIDATES.value: (
            recognize_pb2.SUBJECT_DIAGNOSTIC_MULTIPLE_CANDIDATES
        ),
    },
)
FIELD_STATUS = MappingProxyType(
    {
        "extracted": recognize_pb2.FIELD_STATUS_EXTRACTED,
        "absent": recognize_pb2.FIELD_STATUS_ABSENT,
        "unreadable": recognize_pb2.FIELD_STATUS_UNREADABLE,
        "conflict": recognize_pb2.FIELD_STATUS_CONFLICT,
        "not_applicable": recognize_pb2.FIELD_STATUS_NOT_APPLICABLE,
        "not_processed": recognize_pb2.FIELD_STATUS_NOT_PROCESSED,
    },
)
VALIDATION_STATUS = MappingProxyType(
    {
        "valid": recognize_pb2.VALIDATION_STATUS_VALID,
        "invalid": recognize_pb2.VALIDATION_STATUS_INVALID,
        "not_applicable": recognize_pb2.VALIDATION_STATUS_NOT_APPLICABLE,
        "not_run": recognize_pb2.VALIDATION_STATUS_NOT_RUN,
    },
)
