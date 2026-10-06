import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class OperationStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    OPERATION_STATUS_UNSPECIFIED: _ClassVar[OperationStatus]
    OPERATION_STATUS_OK: _ClassVar[OperationStatus]
    OPERATION_STATUS_PARTIAL: _ClassVar[OperationStatus]
    OPERATION_STATUS_FAILED: _ClassVar[OperationStatus]
    OPERATION_STATUS_CANCELLED: _ClassVar[OperationStatus]
    OPERATION_STATUS_LIMIT_EXCEEDED: _ClassVar[OperationStatus]

class TaskOutcome(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TASK_OUTCOME_UNSPECIFIED: _ClassVar[TaskOutcome]
    TASK_OUTCOME_COMPLETED: _ClassVar[TaskOutcome]
    TASK_OUTCOME_SUBJECT_REJECTED: _ClassVar[TaskOutcome]
    TASK_OUTCOME_FAILED: _ClassVar[TaskOutcome]
    TASK_OUTCOME_CANCELLED: _ClassVar[TaskOutcome]
    TASK_OUTCOME_LIMIT_EXCEEDED: _ClassVar[TaskOutcome]

class ResultCompleteness(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RESULT_COMPLETENESS_UNSPECIFIED: _ClassVar[ResultCompleteness]
    RESULT_COMPLETENESS_COMPLETE: _ClassVar[ResultCompleteness]
    RESULT_COMPLETENESS_PARTIAL: _ClassVar[ResultCompleteness]
    RESULT_COMPLETENESS_NONE: _ClassVar[ResultCompleteness]

class TechnicalCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TECHNICAL_CODE_UNSPECIFIED: _ClassVar[TechnicalCode]
    TECHNICAL_CODE_INVALID_INPUT: _ClassVar[TechnicalCode]
    TECHNICAL_CODE_INPUT_LIMIT_EXCEEDED: _ClassVar[TechnicalCode]
    TECHNICAL_CODE_INVALID_CONFIGURATION: _ClassVar[TechnicalCode]
    TECHNICAL_CODE_CAPABILITY_MISMATCH: _ClassVar[TechnicalCode]
    TECHNICAL_CODE_MATERIAL_UNAVAILABLE: _ClassVar[TechnicalCode]
    TECHNICAL_CODE_MODEL_UNAVAILABLE: _ClassVar[TechnicalCode]
    TECHNICAL_CODE_EXECUTION_LIMIT_EXCEEDED: _ClassVar[TechnicalCode]
    TECHNICAL_CODE_CANCELLED: _ClassVar[TechnicalCode]
    TECHNICAL_CODE_EXECUTION_ERROR: _ClassVar[TechnicalCode]
    TECHNICAL_CODE_AUTHORIZATION_FAILED: _ClassVar[TechnicalCode]

class TechnicalReasonClass(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TECHNICAL_REASON_CLASS_UNSPECIFIED: _ClassVar[TechnicalReasonClass]
    TECHNICAL_REASON_CLASS_TRANSIENT: _ClassVar[TechnicalReasonClass]
    TECHNICAL_REASON_CLASS_PERMANENT: _ClassVar[TechnicalReasonClass]

class SubjectDiagnostic(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SUBJECT_DIAGNOSTIC_UNSPECIFIED: _ClassVar[SubjectDiagnostic]
    SUBJECT_DIAGNOSTIC_SUPPORTED: _ClassVar[SubjectDiagnostic]
    SUBJECT_DIAGNOSTIC_TARGET_NOT_DETECTED: _ClassVar[SubjectDiagnostic]
    SUBJECT_DIAGNOSTIC_FORM_AMBIGUOUS: _ClassVar[SubjectDiagnostic]
    SUBJECT_DIAGNOSTIC_FORM_UNSUPPORTED: _ClassVar[SubjectDiagnostic]
    SUBJECT_DIAGNOSTIC_FORM_UNRESOLVED: _ClassVar[SubjectDiagnostic]
    SUBJECT_DIAGNOSTIC_MULTIPLE_CANDIDATES: _ClassVar[SubjectDiagnostic]

class FieldStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FIELD_STATUS_UNSPECIFIED: _ClassVar[FieldStatus]
    FIELD_STATUS_EXTRACTED: _ClassVar[FieldStatus]
    FIELD_STATUS_ABSENT: _ClassVar[FieldStatus]
    FIELD_STATUS_UNREADABLE: _ClassVar[FieldStatus]
    FIELD_STATUS_CONFLICT: _ClassVar[FieldStatus]
    FIELD_STATUS_NOT_APPLICABLE: _ClassVar[FieldStatus]
    FIELD_STATUS_NOT_PROCESSED: _ClassVar[FieldStatus]

class ValidationStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    VALIDATION_STATUS_UNSPECIFIED: _ClassVar[ValidationStatus]
    VALIDATION_STATUS_VALID: _ClassVar[ValidationStatus]
    VALIDATION_STATUS_INVALID: _ClassVar[ValidationStatus]
    VALIDATION_STATUS_NOT_APPLICABLE: _ClassVar[ValidationStatus]
    VALIDATION_STATUS_NOT_RUN: _ClassVar[ValidationStatus]

class DiagnosticScope(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DIAGNOSTIC_SCOPE_UNSPECIFIED: _ClassVar[DiagnosticScope]
    DIAGNOSTIC_SCOPE_SUBJECT: _ClassVar[DiagnosticScope]
    DIAGNOSTIC_SCOPE_FIELD: _ClassVar[DiagnosticScope]
    DIAGNOSTIC_SCOPE_STAGE: _ClassVar[DiagnosticScope]
    DIAGNOSTIC_SCOPE_ARTIFACT: _ClassVar[DiagnosticScope]
OPERATION_STATUS_UNSPECIFIED: OperationStatus
OPERATION_STATUS_OK: OperationStatus
OPERATION_STATUS_PARTIAL: OperationStatus
OPERATION_STATUS_FAILED: OperationStatus
OPERATION_STATUS_CANCELLED: OperationStatus
OPERATION_STATUS_LIMIT_EXCEEDED: OperationStatus
TASK_OUTCOME_UNSPECIFIED: TaskOutcome
TASK_OUTCOME_COMPLETED: TaskOutcome
TASK_OUTCOME_SUBJECT_REJECTED: TaskOutcome
TASK_OUTCOME_FAILED: TaskOutcome
TASK_OUTCOME_CANCELLED: TaskOutcome
TASK_OUTCOME_LIMIT_EXCEEDED: TaskOutcome
RESULT_COMPLETENESS_UNSPECIFIED: ResultCompleteness
RESULT_COMPLETENESS_COMPLETE: ResultCompleteness
RESULT_COMPLETENESS_PARTIAL: ResultCompleteness
RESULT_COMPLETENESS_NONE: ResultCompleteness
TECHNICAL_CODE_UNSPECIFIED: TechnicalCode
TECHNICAL_CODE_INVALID_INPUT: TechnicalCode
TECHNICAL_CODE_INPUT_LIMIT_EXCEEDED: TechnicalCode
TECHNICAL_CODE_INVALID_CONFIGURATION: TechnicalCode
TECHNICAL_CODE_CAPABILITY_MISMATCH: TechnicalCode
TECHNICAL_CODE_MATERIAL_UNAVAILABLE: TechnicalCode
TECHNICAL_CODE_MODEL_UNAVAILABLE: TechnicalCode
TECHNICAL_CODE_EXECUTION_LIMIT_EXCEEDED: TechnicalCode
TECHNICAL_CODE_CANCELLED: TechnicalCode
TECHNICAL_CODE_EXECUTION_ERROR: TechnicalCode
TECHNICAL_CODE_AUTHORIZATION_FAILED: TechnicalCode
TECHNICAL_REASON_CLASS_UNSPECIFIED: TechnicalReasonClass
TECHNICAL_REASON_CLASS_TRANSIENT: TechnicalReasonClass
TECHNICAL_REASON_CLASS_PERMANENT: TechnicalReasonClass
SUBJECT_DIAGNOSTIC_UNSPECIFIED: SubjectDiagnostic
SUBJECT_DIAGNOSTIC_SUPPORTED: SubjectDiagnostic
SUBJECT_DIAGNOSTIC_TARGET_NOT_DETECTED: SubjectDiagnostic
SUBJECT_DIAGNOSTIC_FORM_AMBIGUOUS: SubjectDiagnostic
SUBJECT_DIAGNOSTIC_FORM_UNSUPPORTED: SubjectDiagnostic
SUBJECT_DIAGNOSTIC_FORM_UNRESOLVED: SubjectDiagnostic
SUBJECT_DIAGNOSTIC_MULTIPLE_CANDIDATES: SubjectDiagnostic
FIELD_STATUS_UNSPECIFIED: FieldStatus
FIELD_STATUS_EXTRACTED: FieldStatus
FIELD_STATUS_ABSENT: FieldStatus
FIELD_STATUS_UNREADABLE: FieldStatus
FIELD_STATUS_CONFLICT: FieldStatus
FIELD_STATUS_NOT_APPLICABLE: FieldStatus
FIELD_STATUS_NOT_PROCESSED: FieldStatus
VALIDATION_STATUS_UNSPECIFIED: ValidationStatus
VALIDATION_STATUS_VALID: ValidationStatus
VALIDATION_STATUS_INVALID: ValidationStatus
VALIDATION_STATUS_NOT_APPLICABLE: ValidationStatus
VALIDATION_STATUS_NOT_RUN: ValidationStatus
DIAGNOSTIC_SCOPE_UNSPECIFIED: DiagnosticScope
DIAGNOSTIC_SCOPE_SUBJECT: DiagnosticScope
DIAGNOSTIC_SCOPE_FIELD: DiagnosticScope
DIAGNOSTIC_SCOPE_STAGE: DiagnosticScope
DIAGNOSTIC_SCOPE_ARTIFACT: DiagnosticScope

class RecognizeRequest(_message.Message):
    __slots__ = ("contract_version", "task_id", "request_id", "attempt_id", "artifact_ref", "processing_policy")
    CONTRACT_VERSION_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    ATTEMPT_ID_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_REF_FIELD_NUMBER: _ClassVar[int]
    PROCESSING_POLICY_FIELD_NUMBER: _ClassVar[int]
    contract_version: str
    task_id: str
    request_id: str
    attempt_id: str
    artifact_ref: ArtifactRef
    processing_policy: ProcessingPolicy
    def __init__(self, contract_version: _Optional[str] = ..., task_id: _Optional[str] = ..., request_id: _Optional[str] = ..., attempt_id: _Optional[str] = ..., artifact_ref: _Optional[_Union[ArtifactRef, _Mapping]] = ..., processing_policy: _Optional[_Union[ProcessingPolicy, _Mapping]] = ...) -> None: ...

class ArtifactRef(_message.Message):
    __slots__ = ("capability", "task_id", "request_id", "audience", "expires_at", "sha256", "media_type", "size_bytes", "object_generation", "issuer")
    CAPABILITY_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    AUDIENCE_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    SHA256_FIELD_NUMBER: _ClassVar[int]
    MEDIA_TYPE_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    OBJECT_GENERATION_FIELD_NUMBER: _ClassVar[int]
    ISSUER_FIELD_NUMBER: _ClassVar[int]
    capability: str
    task_id: str
    request_id: str
    audience: str
    expires_at: _timestamp_pb2.Timestamp
    sha256: str
    media_type: str
    size_bytes: int
    object_generation: str
    issuer: str
    def __init__(self, capability: _Optional[str] = ..., task_id: _Optional[str] = ..., request_id: _Optional[str] = ..., audience: _Optional[str] = ..., expires_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., sha256: _Optional[str] = ..., media_type: _Optional[str] = ..., size_bytes: _Optional[int] = ..., object_generation: _Optional[str] = ..., issuer: _Optional[str] = ...) -> None: ...

class ProcessingPolicy(_message.Message):
    __slots__ = ("input_policy_id", "input_policy_version", "classifier_policy_id", "classifier_policy_version", "limits", "diagnostic_retention_policy")
    INPUT_POLICY_ID_FIELD_NUMBER: _ClassVar[int]
    INPUT_POLICY_VERSION_FIELD_NUMBER: _ClassVar[int]
    CLASSIFIER_POLICY_ID_FIELD_NUMBER: _ClassVar[int]
    CLASSIFIER_POLICY_VERSION_FIELD_NUMBER: _ClassVar[int]
    LIMITS_FIELD_NUMBER: _ClassVar[int]
    DIAGNOSTIC_RETENTION_POLICY_FIELD_NUMBER: _ClassVar[int]
    input_policy_id: str
    input_policy_version: str
    classifier_policy_id: str
    classifier_policy_version: str
    limits: ExecutionLimits
    diagnostic_retention_policy: str
    def __init__(self, input_policy_id: _Optional[str] = ..., input_policy_version: _Optional[str] = ..., classifier_policy_id: _Optional[str] = ..., classifier_policy_version: _Optional[str] = ..., limits: _Optional[_Union[ExecutionLimits, _Mapping]] = ..., diagnostic_retention_policy: _Optional[str] = ...) -> None: ...

class ExecutionLimits(_message.Message):
    __slots__ = ("timeout_ms", "memory_limit_bytes", "max_input_bytes", "max_input_pixels", "max_total_pixels", "max_output_pixels", "max_pages", "cpu_threads", "max_model_calls", "max_variants")
    TIMEOUT_MS_FIELD_NUMBER: _ClassVar[int]
    MEMORY_LIMIT_BYTES_FIELD_NUMBER: _ClassVar[int]
    MAX_INPUT_BYTES_FIELD_NUMBER: _ClassVar[int]
    MAX_INPUT_PIXELS_FIELD_NUMBER: _ClassVar[int]
    MAX_TOTAL_PIXELS_FIELD_NUMBER: _ClassVar[int]
    MAX_OUTPUT_PIXELS_FIELD_NUMBER: _ClassVar[int]
    MAX_PAGES_FIELD_NUMBER: _ClassVar[int]
    CPU_THREADS_FIELD_NUMBER: _ClassVar[int]
    MAX_MODEL_CALLS_FIELD_NUMBER: _ClassVar[int]
    MAX_VARIANTS_FIELD_NUMBER: _ClassVar[int]
    timeout_ms: int
    memory_limit_bytes: int
    max_input_bytes: int
    max_input_pixels: int
    max_total_pixels: int
    max_output_pixels: int
    max_pages: int
    cpu_threads: int
    max_model_calls: int
    max_variants: int
    def __init__(self, timeout_ms: _Optional[int] = ..., memory_limit_bytes: _Optional[int] = ..., max_input_bytes: _Optional[int] = ..., max_input_pixels: _Optional[int] = ..., max_total_pixels: _Optional[int] = ..., max_output_pixels: _Optional[int] = ..., max_pages: _Optional[int] = ..., cpu_threads: _Optional[int] = ..., max_model_calls: _Optional[int] = ..., max_variants: _Optional[int] = ...) -> None: ...

class RecognizeResponse(_message.Message):
    __slots__ = ("contract_version", "task_id", "request_id", "attempt_id", "operation_status", "task_outcome", "result_completeness", "form_resolution", "fields", "diagnostics", "execution", "technical_code", "technical_code_raw", "subject_diagnostic", "technical_reason", "technical_reason_class")
    CONTRACT_VERSION_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    ATTEMPT_ID_FIELD_NUMBER: _ClassVar[int]
    OPERATION_STATUS_FIELD_NUMBER: _ClassVar[int]
    TASK_OUTCOME_FIELD_NUMBER: _ClassVar[int]
    RESULT_COMPLETENESS_FIELD_NUMBER: _ClassVar[int]
    FORM_RESOLUTION_FIELD_NUMBER: _ClassVar[int]
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    DIAGNOSTICS_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_FIELD_NUMBER: _ClassVar[int]
    TECHNICAL_CODE_FIELD_NUMBER: _ClassVar[int]
    TECHNICAL_CODE_RAW_FIELD_NUMBER: _ClassVar[int]
    SUBJECT_DIAGNOSTIC_FIELD_NUMBER: _ClassVar[int]
    TECHNICAL_REASON_FIELD_NUMBER: _ClassVar[int]
    TECHNICAL_REASON_CLASS_FIELD_NUMBER: _ClassVar[int]
    contract_version: str
    task_id: str
    request_id: str
    attempt_id: str
    operation_status: OperationStatus
    task_outcome: TaskOutcome
    result_completeness: ResultCompleteness
    form_resolution: FormResolution
    fields: _containers.RepeatedCompositeFieldContainer[FieldResult]
    diagnostics: _containers.RepeatedCompositeFieldContainer[Diagnostic]
    execution: ExecutionMetadata
    technical_code: TechnicalCode
    technical_code_raw: str
    subject_diagnostic: SubjectDiagnostic
    technical_reason: str
    technical_reason_class: TechnicalReasonClass
    def __init__(self, contract_version: _Optional[str] = ..., task_id: _Optional[str] = ..., request_id: _Optional[str] = ..., attempt_id: _Optional[str] = ..., operation_status: _Optional[_Union[OperationStatus, str]] = ..., task_outcome: _Optional[_Union[TaskOutcome, str]] = ..., result_completeness: _Optional[_Union[ResultCompleteness, str]] = ..., form_resolution: _Optional[_Union[FormResolution, _Mapping]] = ..., fields: _Optional[_Iterable[_Union[FieldResult, _Mapping]]] = ..., diagnostics: _Optional[_Iterable[_Union[Diagnostic, _Mapping]]] = ..., execution: _Optional[_Union[ExecutionMetadata, _Mapping]] = ..., technical_code: _Optional[_Union[TechnicalCode, str]] = ..., technical_code_raw: _Optional[str] = ..., subject_diagnostic: _Optional[_Union[SubjectDiagnostic, str]] = ..., technical_reason: _Optional[str] = ..., technical_reason_class: _Optional[_Union[TechnicalReasonClass, str]] = ...) -> None: ...

class FormResolution(_message.Message):
    __slots__ = ("status", "form_id", "calibration_ref", "decision_evidence_ref", "alternatives")
    class ResolutionStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        RESOLUTION_STATUS_UNSPECIFIED: _ClassVar[FormResolution.ResolutionStatus]
        RESOLUTION_STATUS_RESOLVED: _ClassVar[FormResolution.ResolutionStatus]
        RESOLUTION_STATUS_AMBIGUOUS: _ClassVar[FormResolution.ResolutionStatus]
        RESOLUTION_STATUS_UNRESOLVED: _ClassVar[FormResolution.ResolutionStatus]
        RESOLUTION_STATUS_UNSUPPORTED: _ClassVar[FormResolution.ResolutionStatus]
    RESOLUTION_STATUS_UNSPECIFIED: FormResolution.ResolutionStatus
    RESOLUTION_STATUS_RESOLVED: FormResolution.ResolutionStatus
    RESOLUTION_STATUS_AMBIGUOUS: FormResolution.ResolutionStatus
    RESOLUTION_STATUS_UNRESOLVED: FormResolution.ResolutionStatus
    RESOLUTION_STATUS_UNSUPPORTED: FormResolution.ResolutionStatus
    STATUS_FIELD_NUMBER: _ClassVar[int]
    FORM_ID_FIELD_NUMBER: _ClassVar[int]
    CALIBRATION_REF_FIELD_NUMBER: _ClassVar[int]
    DECISION_EVIDENCE_REF_FIELD_NUMBER: _ClassVar[int]
    ALTERNATIVES_FIELD_NUMBER: _ClassVar[int]
    status: FormResolution.ResolutionStatus
    form_id: str
    calibration_ref: str
    decision_evidence_ref: str
    alternatives: _containers.RepeatedCompositeFieldContainer[FormHypothesis]
    def __init__(self, status: _Optional[_Union[FormResolution.ResolutionStatus, str]] = ..., form_id: _Optional[str] = ..., calibration_ref: _Optional[str] = ..., decision_evidence_ref: _Optional[str] = ..., alternatives: _Optional[_Iterable[_Union[FormHypothesis, _Mapping]]] = ...) -> None: ...

class FormHypothesis(_message.Message):
    __slots__ = ("form_id", "decision_score", "score_scale", "evidence_ref")
    FORM_ID_FIELD_NUMBER: _ClassVar[int]
    DECISION_SCORE_FIELD_NUMBER: _ClassVar[int]
    SCORE_SCALE_FIELD_NUMBER: _ClassVar[int]
    EVIDENCE_REF_FIELD_NUMBER: _ClassVar[int]
    form_id: str
    decision_score: float
    score_scale: str
    evidence_ref: str
    def __init__(self, form_id: _Optional[str] = ..., decision_score: _Optional[float] = ..., score_scale: _Optional[str] = ..., evidence_ref: _Optional[str] = ...) -> None: ...

class FieldResult(_message.Message):
    __slots__ = ("field_id", "status", "raw_value", "value", "evidence_refs", "validations", "diagnostics", "selected_candidate_id", "confidence", "correction_refs", "normalization_refs")
    FIELD_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    RAW_VALUE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    EVIDENCE_REFS_FIELD_NUMBER: _ClassVar[int]
    VALIDATIONS_FIELD_NUMBER: _ClassVar[int]
    DIAGNOSTICS_FIELD_NUMBER: _ClassVar[int]
    SELECTED_CANDIDATE_ID_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    CORRECTION_REFS_FIELD_NUMBER: _ClassVar[int]
    NORMALIZATION_REFS_FIELD_NUMBER: _ClassVar[int]
    field_id: str
    status: FieldStatus
    raw_value: str
    value: str
    evidence_refs: _containers.RepeatedScalarFieldContainer[str]
    validations: _containers.RepeatedCompositeFieldContainer[ValidationResult]
    diagnostics: _containers.RepeatedCompositeFieldContainer[Diagnostic]
    selected_candidate_id: str
    confidence: Confidence
    correction_refs: _containers.RepeatedScalarFieldContainer[str]
    normalization_refs: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, field_id: _Optional[str] = ..., status: _Optional[_Union[FieldStatus, str]] = ..., raw_value: _Optional[str] = ..., value: _Optional[str] = ..., evidence_refs: _Optional[_Iterable[str]] = ..., validations: _Optional[_Iterable[_Union[ValidationResult, _Mapping]]] = ..., diagnostics: _Optional[_Iterable[_Union[Diagnostic, _Mapping]]] = ..., selected_candidate_id: _Optional[str] = ..., confidence: _Optional[_Union[Confidence, _Mapping]] = ..., correction_refs: _Optional[_Iterable[str]] = ..., normalization_refs: _Optional[_Iterable[str]] = ...) -> None: ...

class Confidence(_message.Message):
    __slots__ = ("decision_score", "score_scale", "probability", "calibration_id", "calibration_scope")
    DECISION_SCORE_FIELD_NUMBER: _ClassVar[int]
    SCORE_SCALE_FIELD_NUMBER: _ClassVar[int]
    PROBABILITY_FIELD_NUMBER: _ClassVar[int]
    CALIBRATION_ID_FIELD_NUMBER: _ClassVar[int]
    CALIBRATION_SCOPE_FIELD_NUMBER: _ClassVar[int]
    decision_score: float
    score_scale: str
    probability: float
    calibration_id: str
    calibration_scope: str
    def __init__(self, decision_score: _Optional[float] = ..., score_scale: _Optional[str] = ..., probability: _Optional[float] = ..., calibration_id: _Optional[str] = ..., calibration_scope: _Optional[str] = ...) -> None: ...

class ValidationResult(_message.Message):
    __slots__ = ("rule_id", "rule_version", "status", "reason", "input_candidate_ids")
    RULE_ID_FIELD_NUMBER: _ClassVar[int]
    RULE_VERSION_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    INPUT_CANDIDATE_IDS_FIELD_NUMBER: _ClassVar[int]
    rule_id: str
    rule_version: str
    status: ValidationStatus
    reason: str
    input_candidate_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, rule_id: _Optional[str] = ..., rule_version: _Optional[str] = ..., status: _Optional[_Union[ValidationStatus, str]] = ..., reason: _Optional[str] = ..., input_candidate_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class Diagnostic(_message.Message):
    __slots__ = ("code", "scope", "evidence_ref", "reason")
    CODE_FIELD_NUMBER: _ClassVar[int]
    SCOPE_FIELD_NUMBER: _ClassVar[int]
    EVIDENCE_REF_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    code: str
    scope: DiagnosticScope
    evidence_ref: str
    reason: str
    def __init__(self, code: _Optional[str] = ..., scope: _Optional[_Union[DiagnosticScope, str]] = ..., evidence_ref: _Optional[str] = ..., reason: _Optional[str] = ...) -> None: ...

class ExecutionMetadata(_message.Message):
    __slots__ = ("applied_execution_ref", "specification_hash", "implementation_version", "model_version", "calibration_version", "device", "elapsed_ms", "model_calls", "cache_hit")
    APPLIED_EXECUTION_REF_FIELD_NUMBER: _ClassVar[int]
    SPECIFICATION_HASH_FIELD_NUMBER: _ClassVar[int]
    IMPLEMENTATION_VERSION_FIELD_NUMBER: _ClassVar[int]
    MODEL_VERSION_FIELD_NUMBER: _ClassVar[int]
    CALIBRATION_VERSION_FIELD_NUMBER: _ClassVar[int]
    DEVICE_FIELD_NUMBER: _ClassVar[int]
    ELAPSED_MS_FIELD_NUMBER: _ClassVar[int]
    MODEL_CALLS_FIELD_NUMBER: _ClassVar[int]
    CACHE_HIT_FIELD_NUMBER: _ClassVar[int]
    applied_execution_ref: str
    specification_hash: str
    implementation_version: str
    model_version: str
    calibration_version: str
    device: str
    elapsed_ms: int
    model_calls: int
    cache_hit: bool
    def __init__(self, applied_execution_ref: _Optional[str] = ..., specification_hash: _Optional[str] = ..., implementation_version: _Optional[str] = ..., model_version: _Optional[str] = ..., calibration_version: _Optional[str] = ..., device: _Optional[str] = ..., elapsed_ms: _Optional[int] = ..., model_calls: _Optional[int] = ..., cache_hit: _Optional[bool] = ...) -> None: ...
