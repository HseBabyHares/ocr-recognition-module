import pytest

from sird_recognition.codes import (
    GrpcStatus,
    OperationStatus,
    ResultCompleteness,
    TaskOutcome,
    TechnicalCode,
    TechnicalReasonClass,
)
from sird_recognition.retry import classify_grpc, classify_technical


@pytest.mark.parametrize(
    ("code", "operation_status", "task_outcome"),
    [
        (
            TechnicalCode.INVALID_INPUT,
            OperationStatus.FAILED,
            TaskOutcome.FAILED,
        ),
        (
            TechnicalCode.INVALID_CONFIGURATION,
            OperationStatus.FAILED,
            TaskOutcome.FAILED,
        ),
        (
            TechnicalCode.CAPABILITY_MISMATCH,
            OperationStatus.FAILED,
            TaskOutcome.FAILED,
        ),
        (
            TechnicalCode.AUTHORIZATION_FAILED,
            OperationStatus.FAILED,
            TaskOutcome.FAILED,
        ),
        (
            TechnicalCode.INPUT_LIMIT_EXCEEDED,
            OperationStatus.LIMIT_EXCEEDED,
            TaskOutcome.LIMIT_EXCEEDED,
        ),
        (
            TechnicalCode.EXECUTION_LIMIT_EXCEEDED,
            OperationStatus.LIMIT_EXCEEDED,
            TaskOutcome.LIMIT_EXCEEDED,
        ),
        (
            TechnicalCode.CANCELLED,
            OperationStatus.CANCELLED,
            TaskOutcome.CANCELLED,
        ),
    ],
)
def test_technical_terminal_rows(
    code: TechnicalCode,
    operation_status: OperationStatus,
    task_outcome: TaskOutcome,
) -> None:
    decision = classify_technical(
        code,
        reason_class=TechnicalReasonClass.TRANSIENT,
        attempts_remaining=True,
    )

    assert decision.retry is False
    assert decision.operation_status is operation_status
    assert decision.task_outcome is task_outcome
    assert decision.result_completeness is ResultCompleteness.NONE


@pytest.mark.parametrize(
    "code",
    [
        TechnicalCode.MATERIAL_UNAVAILABLE,
        TechnicalCode.MODEL_UNAVAILABLE,
        TechnicalCode.EXECUTION_ERROR,
    ],
)
def test_transient_technical_rows_retry(code: TechnicalCode) -> None:
    decision = classify_technical(
        code,
        reason_class=TechnicalReasonClass.TRANSIENT,
        attempts_remaining=True,
    )

    assert decision.retry is True
    assert decision.operation_status is OperationStatus.FAILED
    assert decision.task_outcome is None
    assert decision.result_completeness is None


@pytest.mark.parametrize(
    "reason_class",
    [TechnicalReasonClass.UNSPECIFIED, TechnicalReasonClass.PERMANENT],
)
@pytest.mark.parametrize(
    "code",
    [
        TechnicalCode.MATERIAL_UNAVAILABLE,
        TechnicalCode.MODEL_UNAVAILABLE,
        TechnicalCode.EXECUTION_ERROR,
    ],
)
def test_nontransient_technical_rows_fail(
    code: TechnicalCode,
    reason_class: TechnicalReasonClass,
) -> None:
    decision = classify_technical(
        code,
        reason_class=reason_class,
        attempts_remaining=True,
    )

    assert decision.retry is False
    assert decision.task_outcome is TaskOutcome.FAILED
    assert decision.result_completeness is ResultCompleteness.NONE


@pytest.mark.parametrize(
    "status",
    [GrpcStatus.UNAVAILABLE, GrpcStatus.DEADLINE_EXCEEDED],
)
def test_retryable_grpc_rows_use_budget(status: GrpcStatus) -> None:
    retry = classify_grpc(status, attempts_remaining=True)
    terminal = classify_grpc(status, attempts_remaining=False)

    assert retry.retry is True
    assert retry.task_outcome is None
    assert terminal.retry is False
    assert terminal.task_outcome is TaskOutcome.FAILED


@pytest.mark.parametrize(
    "status",
    [
        GrpcStatus.CANCELLED,
        GrpcStatus.UNKNOWN,
        GrpcStatus.INVALID_ARGUMENT,
        GrpcStatus.NOT_FOUND,
        GrpcStatus.ALREADY_EXISTS,
        GrpcStatus.PERMISSION_DENIED,
        GrpcStatus.RESOURCE_EXHAUSTED,
        GrpcStatus.FAILED_PRECONDITION,
        GrpcStatus.ABORTED,
        GrpcStatus.OUT_OF_RANGE,
        GrpcStatus.UNIMPLEMENTED,
        GrpcStatus.INTERNAL,
        GrpcStatus.DATA_LOSS,
        GrpcStatus.UNAUTHENTICATED,
    ],
)
def test_nonretryable_grpc_rows_fail(status: GrpcStatus) -> None:
    decision = classify_grpc(status, attempts_remaining=True)

    assert decision.retry is False
    assert decision.task_outcome is TaskOutcome.FAILED
    assert decision.result_completeness is ResultCompleteness.NONE


def test_cancellation_overrides_grpc_retry() -> None:
    decision = classify_grpc(
        GrpcStatus.DEADLINE_EXCEEDED,
        attempts_remaining=True,
        caller_cancelled=True,
    )

    assert decision.retry is False
    assert decision.operation_status is OperationStatus.CANCELLED
    assert decision.task_outcome is TaskOutcome.CANCELLED


def test_unknown_grpc_status_fails_closed() -> None:
    decision = classify_grpc("FUTURE_STATUS", attempts_remaining=True)

    assert decision.retry is False
    assert decision.task_outcome is TaskOutcome.FAILED
