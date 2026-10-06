"""Synchronous gRPC boundary for the transport-neutral OCR runtime."""

from __future__ import annotations

import importlib
import sys
from typing import Any, Protocol

import grpc

from sird_recognition import _runtime_models
from sird_recognition.contracts.stages import StageContext

from . import (  # noqa: WPS300
    _grpc_adapter_limits,
    _grpc_adapter_request,
    _grpc_adapter_response,
)
from ._proto.sird.ocr.v1 import recognize_pb2  # noqa: WPS300


def _load_generated_grpc() -> Any:
    generated_aliases = {
        "sird": sys.modules["sird_recognition._proto.sird"],
        "sird.ocr": sys.modules["sird_recognition._proto.sird.ocr"],
        "sird.ocr.v1": sys.modules["sird_recognition._proto.sird.ocr.v1"],
        "sird.ocr.v1.recognize_pb2": recognize_pb2,
    }
    previous_aliases = {
        alias_name: sys.modules.get(alias_name)
        for alias_name in generated_aliases
    }
    sys.modules.update(generated_aliases)
    try:
        grpc_module = importlib.import_module(
            "._proto.sird.ocr.v1.recognize_pb2_grpc",
            __package__,
        )
    except BaseException:
        for alias_name, previous_module in previous_aliases.items():
            if previous_module is None:
                sys.modules.pop(alias_name, None)
            else:
                sys.modules[alias_name] = previous_module
        raise
    for alias_name, previous_module in previous_aliases.items():
        if previous_module is None:
            sys.modules.pop(alias_name, None)
        else:
            sys.modules[alias_name] = previous_module
    return grpc_module


_recognize_pb2_grpc = _load_generated_grpc()
OcrServiceStub = _recognize_pb2_grpc.OcrServiceStub


class RecognitionRuntime(Protocol):
    """Port used by the adapter to invoke one stateless recognition call."""

    def recognize(
        self,
        request: _runtime_models.RecognizeRequest,
        context: StageContext,
    ) -> _runtime_models.RecognitionResponse:
        """Run the transport-neutral runtime."""


def register_ocr_service(
    server: grpc.Server,
    runtime: RecognitionRuntime,
) -> None:
    """Register one runtime-backed OCR servicer on a synchronous server."""
    _recognize_pb2_grpc.add_OcrServiceServicer_to_server(
        OcrServiceServicer(runtime),
        server,
    )


class OcrServiceServicer(_recognize_pb2_grpc.OcrServiceServicer):
    """Translate the unary protobuf call to the stateless runtime."""

    def __init__(self, runtime: RecognitionRuntime) -> None:
        self._runtime = runtime

    def Recognize(
        self,
        request: recognize_pb2.RecognizeRequest,
        context: grpc.ServicerContext,
    ) -> recognize_pb2.RecognizeResponse:
        """Handle one bounded unary recognition request."""
        _grpc_adapter_limits.ensure_active(context)
        try:
            domain_request, stage_context = (
                _grpc_adapter_request.parse_request(
                    request,
                )
            )
        except ValueError as error:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(error))
            raise AssertionError(
                "context.abort returned unexpectedly"
            ) from error
        _grpc_adapter_limits.ensure_active(context)
        _grpc_adapter_limits.ensure_deadline(context)
        domain_request, stage_context = _grpc_adapter_limits.clamp_timeout(
            domain_request,
            stage_context,
            context.time_remaining(),
        )
        response = self._recognize(domain_request, stage_context, context)
        _grpc_adapter_limits.ensure_active(context)
        return _grpc_adapter_response.map_response(
            response,
            stage_context,
            domain_request.task_id,
        )

    def _recognize(
        self,
        request: _runtime_models.RecognizeRequest,
        context_data: StageContext,
        context: grpc.ServicerContext,
    ) -> _runtime_models.RecognitionResponse:
        try:
            return self._runtime.recognize(request, context_data)
        except grpc.RpcError:
            raise
        except Exception as error:
            context.abort(grpc.StatusCode.INTERNAL, "OCR runtime failed")
            raise AssertionError(
                "context.abort returned unexpectedly"
            ) from error
