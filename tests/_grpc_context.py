from __future__ import annotations

from dataclasses import dataclass

import grpc

from sird_recognition import _runtime_models
from sird_recognition.contracts import stages


@dataclass
class AbortError(Exception):
    code_value: grpc.StatusCode
    details_value: str


class FakeContext:
    def __init__(
        self,
        *,
        active: bool = True,
        remaining: float | None = None,
    ) -> None:
        self.active = active
        self.remaining = remaining

    def is_active(self) -> bool:
        return self.active

    def time_remaining(self) -> float | None:
        return self.remaining

    def abort(self, code: grpc.StatusCode, details: str) -> None:
        raise AbortError(code, details)


class FakeRuntime:
    def __init__(
        self,
        response: _runtime_models.RecognitionResponse,
        *,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.request: _runtime_models.RecognizeRequest | None = None
        self.context: stages.StageContext | None = None

    def recognize(
        self,
        request: _runtime_models.RecognizeRequest,
        context: stages.StageContext,
    ) -> _runtime_models.RecognitionResponse:
        if self.error is not None:
            raise self.error
        self.request = request
        self.context = context
        return self.response
