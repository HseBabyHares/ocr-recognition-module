"""Execution limit translation and transport guard helpers."""

from __future__ import annotations

from dataclasses import replace

import grpc

from sird_recognition import _grpc_adapter_contract as _contract
from sird_recognition import _runtime_models
from sird_recognition._proto.sird.ocr.v1 import recognize_pb2
from sird_recognition.contracts.stages import StageContext


def map_limits(
    limits: recognize_pb2.ExecutionLimits,
) -> dict[str, int | float]:
    limit_values = {
        field_name: int(getattr(limits, field_name))
        for field_name in _contract.LIMIT_FIELDS
    }
    for field_name in _contract.REQUIRED_LIMIT_FIELDS:
        if limit_values[field_name] <= 0:
            raise ValueError(
                (f"processing_policy.limits.{field_name} must be positive"),
            )
    timeout_millis = limit_values.pop("timeout_ms")
    return {
        "timeout_seconds": (
            timeout_millis / _contract.MILLISECONDS_PER_SECOND
        ),
        **limit_values,
    }


def clamp_timeout(
    request: _runtime_models.RecognizeRequest,
    context: StageContext,
    remaining: float | None,
) -> tuple[_runtime_models.RecognizeRequest, StageContext]:
    timeout_seconds = context.limits["timeout_seconds"]
    if remaining is None or remaining >= timeout_seconds:
        return request, context
    bounded_limits = dict(context.limits)
    bounded_limits["timeout_seconds"] = remaining
    return (
        replace(request, limits=bounded_limits),
        replace(context, limits=bounded_limits),
    )


def ensure_active(context: grpc.ServicerContext) -> None:
    if not context.is_active():
        context.abort(
            grpc.StatusCode.CANCELLED,
            "recognition call cancelled",
        )


def ensure_deadline(context: grpc.ServicerContext) -> None:
    remaining = context.time_remaining()
    if remaining is not None and remaining <= 0:
        context.abort(
            grpc.StatusCode.DEADLINE_EXCEEDED,
            "recognition deadline exceeded",
        )
