"""Deterministic technical and transport outcome classification."""

from dataclasses import dataclass

from sird_recognition.codes import (
    GrpcStatus,
    OperationStatus,
    ResultCompleteness,
    TaskOutcome,
    TechnicalCode,
    TechnicalReasonClass,
)


@dataclass(frozen=True, slots=True)
class RetryDecision:
    """Outcome mapping for one failed attempt."""

    retry: bool
    operation_status: OperationStatus
    task_outcome: TaskOutcome | None
    result_completeness: ResultCompleteness | None
    reason: str


def _failed(reason: str, retry: bool = False) -> RetryDecision:
    return RetryDecision(
        retry=retry,
        operation_status=OperationStatus.FAILED,
        task_outcome=None if retry else TaskOutcome.FAILED,
        result_completeness=None if retry else ResultCompleteness.NONE,
        reason=reason,
    )


def classify_technical(
    code: TechnicalCode,
    *,
    reason_class: TechnicalReasonClass = TechnicalReasonClass.UNSPECIFIED,
    attempts_remaining: bool = False,
) -> RetryDecision:
    """Map a technical code using only its explicit reason class."""
    if code in {
        TechnicalCode.INPUT_LIMIT_EXCEEDED,
        TechnicalCode.EXECUTION_LIMIT_EXCEEDED,
    }:
        return RetryDecision(
            False,
            OperationStatus.LIMIT_EXCEEDED,
            TaskOutcome.LIMIT_EXCEEDED,
            ResultCompleteness.NONE,
            code,
        )
    if code is TechnicalCode.CANCELLED:
        return RetryDecision(
            False,
            OperationStatus.CANCELLED,
            TaskOutcome.CANCELLED,
            ResultCompleteness.NONE,
            code,
        )
    retryable_codes = {
        TechnicalCode.MATERIAL_UNAVAILABLE,
        TechnicalCode.MODEL_UNAVAILABLE,
        TechnicalCode.EXECUTION_ERROR,
    }
    should_retry = (
        code in retryable_codes
        and reason_class is TechnicalReasonClass.TRANSIENT
        and attempts_remaining
    )
    return _failed(code, retry=should_retry)


def classify_grpc(
    status: GrpcStatus | str,
    *,
    attempts_remaining: bool,
    caller_cancelled: bool = False,
) -> RetryDecision:
    """Map a gRPC failure to the shared Process Service attempt policy."""
    if caller_cancelled:
        return RetryDecision(
            False,
            OperationStatus.CANCELLED,
            TaskOutcome.CANCELLED,
            ResultCompleteness.NONE,
            "caller_cancelled",
        )
    retryable_statuses = {
        GrpcStatus.UNAVAILABLE,
        GrpcStatus.DEADLINE_EXCEEDED,
    }
    should_retry = status in retryable_statuses and attempts_remaining
    return _failed(str(status), retry=should_retry)
