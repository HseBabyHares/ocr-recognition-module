"""Domain-to-protobuf response translation helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sird_recognition import _grpc_adapter_contract as _contract
from sird_recognition import _runtime_models
from sird_recognition._grpc_adapter_execution import map_execution
from sird_recognition._proto.sird.ocr.v1 import recognize_pb2
from sird_recognition.contracts.stages import StageContext


def enum_text(enum_value: object) -> str:
    enum_member = getattr(enum_value, "value", enum_value)
    return str(enum_member).lower()


def map_response(
    recognition: _runtime_models.RecognitionResponse,
    stage_context: StageContext,
    task_id: str,
) -> recognize_pb2.RecognizeResponse:
    mapped = recognize_pb2.RecognizeResponse(
        contract_version=stage_context.contract_version,
        task_id=recognition.task_id or task_id,
        request_id=recognition.request_id or stage_context.request_id,
        attempt_id=stage_context.attempt_id,
    )
    mapped.operation_status = _contract.OPERATION_STATUS.get(
        enum_text(recognition.operation_status),
        recognize_pb2.OPERATION_STATUS_UNSPECIFIED,
    )
    if recognition.task_outcome is not None:
        mapped.task_outcome = _contract.TASK_OUTCOME.get(
            enum_text(recognition.task_outcome),
            recognize_pb2.TASK_OUTCOME_UNSPECIFIED,
        )
    if recognition.result_completeness is not None:
        mapped.result_completeness = _contract.RESULT_COMPLETENESS.get(
            enum_text(recognition.result_completeness),
            recognize_pb2.RESULT_COMPLETENESS_UNSPECIFIED,
        )
    map_form(mapped.form_resolution, recognition.form_resolution)
    mapped.fields.extend(
        map_field(field_id, field_result)
        for field_id, field_result in recognition.fields.items()
    )
    mapped.diagnostics.extend(
        recognize_pb2.Diagnostic(
            code=diagnostic_code,
            scope=recognize_pb2.DIAGNOSTIC_SCOPE_STAGE,
        )
        for diagnostic_code in recognition.diagnostics
    )
    map_execution(mapped.execution, recognition.execution)
    map_technical(mapped, recognition)
    if recognition.subject_diagnostic is not None:
        mapped.subject_diagnostic = _contract.SUBJECT_DIAGNOSTIC.get(
            enum_text(recognition.subject_diagnostic),
            recognize_pb2.SUBJECT_DIAGNOSTIC_UNSPECIFIED,
        )
    return mapped


def map_form(target: Any, form_resolution: Any) -> None:
    target.status = _contract.FORM_STATUS.get(
        enum_text(form_resolution.status),
        recognize_pb2.FormResolution.RESOLUTION_STATUS_UNSPECIFIED,
    )
    for field_name in (
        "form_id",
        "calibration_ref",
        "decision_evidence_ref",
    ):
        field_text = getattr(form_resolution, field_name)
        if field_text:
            setattr(target, field_name, field_text)
    target.alternatives.extend(
        recognize_pb2.FormHypothesis(form_id=alternative)
        for alternative in form_resolution.alternatives
    )


def map_field(field_id: str, field_result: Any) -> Any:
    mapped = recognize_pb2.FieldResult(field_id=field_id)
    mapped.status = _contract.FIELD_STATUS.get(
        enum_text(field_result.status),
        recognize_pb2.FIELD_STATUS_UNSPECIFIED,
    )
    field_text = field_result.field_value
    if isinstance(field_text, str):
        mapped.value = field_text
    mapped.evidence_refs.extend(field_result.evidence_refs)
    mapped.diagnostics.extend(
        recognize_pb2.Diagnostic(
            code=diagnostic_code,
            scope=recognize_pb2.DIAGNOSTIC_SCOPE_FIELD,
        )
        for diagnostic_code in field_result.diagnostics
    )
    mapped.validations.extend(
        map_validation(validation) for validation in field_result.validations
    )
    return mapped


def map_validation(validation: object) -> Any:
    if not isinstance(validation, Mapping):
        return recognize_pb2.ValidationResult(reason=str(validation))
    mapped = recognize_pb2.ValidationResult(
        rule_id=str(validation.get("rule_id", "")),
        rule_version=str(validation.get("rule_version", "")),
        reason=str(validation.get("reason", "")),
        input_candidate_ids=tuple(
            str(candidate_id)
            for candidate_id in validation.get("input_candidate_ids", ())
        ),
    )
    validation_status = validation.get("status")
    if validation_status is not None:
        mapped.status = _contract.VALIDATION_STATUS.get(
            enum_text(validation_status),
            recognize_pb2.VALIDATION_STATUS_UNSPECIFIED,
        )
    return mapped


def map_technical(
    target: recognize_pb2.RecognizeResponse,
    recognition: _runtime_models.RecognitionResponse,
) -> None:
    if recognition.technical_reason is not None:
        target.technical_reason = recognition.technical_reason
    if recognition.technical_code is None:
        return
    code_text = enum_text(recognition.technical_code).upper()
    enum_name = f"TECHNICAL_CODE_{code_text}"
    if hasattr(recognize_pb2, enum_name):
        target.technical_code = getattr(recognize_pb2, enum_name)
    else:
        target.technical_code_raw = code_text
    target.technical_reason_class = (
        recognize_pb2.TECHNICAL_REASON_CLASS_TRANSIENT
        if recognition.retryable
        else recognize_pb2.TECHNICAL_REASON_CLASS_PERMANENT
    )
