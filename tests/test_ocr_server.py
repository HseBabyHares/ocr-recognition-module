"""SNILS gRPC service: stages and the wire round trip.

Field values are synthetic; the SNILS number is a checksum-valid example.
"""

from __future__ import annotations

from typing import Any

import grpc

from sird_recognition._snils_types import (
    SnilsRecognitionResult,
    SnilsRecognitionStatus,
)
from sird_recognition.contracts.stages import ExecutionSpec
from sird_recognition.grpc_adapter import OcrServiceStub, recognize_pb2
from sird_recognition.ocr_server import serve
from sird_recognition.runtime import RecognizerRuntime
from sird_recognition.snils_stages import (
    CapabilityPrepare,
    MarkerFormResolve,
    SnilsExecuteProfile,
    TextFormProbe,
)
from tests import _grpc_fixtures as grpc_fixtures
from tests import _ocr_fixtures as fixtures
from tests._object_store import reader

_VERIFIED = SnilsRecognitionResult(
    SnilsRecognitionStatus.VERIFIED,
    "11223344595",
    "Синтетов Тест Тестович",
    "2000-01-02",
    ("snils_checksum_valid",),
    1,
    1,
)
_REFUSED = SnilsRecognitionResult(
    SnilsRecognitionStatus.REFUSED, None, None, None, ("no_snils",), 1, 1
)


_CARD_TEXT = "СТРАХОВОЕ СВИДЕТЕЛЬСТВО"
_NOTICE_TEXT = (
    "Уведомление о регистрации в системе (персонифицированного) учета"
)


class _Service:
    def __init__(self, recognized: SnilsRecognitionResult, text: str) -> None:
        self.recognized = recognized
        self.text = text

    def read_page(self, image: bytes, **_: object) -> tuple[Any, ...]:
        assert image == fixtures.IMAGE
        return fixtures.page_text(self.text)

    def recognize_observations(
        self, observations: tuple[Any, ...], **_: object
    ) -> SnilsRecognitionResult:
        assert observations == fixtures.page_text(self.text)
        return self.recognized


def _runtime(
    store: str, recognized: SnilsRecognitionResult, text: str
) -> RecognizerRuntime:
    service: Any = _Service(recognized, text)
    specification = ExecutionSpec(
        "snils_card", "snils-test", ("execute",), {}, "c"
    )
    return RecognizerRuntime(
        CapabilityPrepare(fixtures.VERIFIER),
        TextFormProbe(service, reader(store)),
        MarkerFormResolve({"snils_card": specification}),
        SnilsExecuteProfile(service, reader(store)),
    )


def _call(
    store: str,
    recognized: SnilsRecognitionResult,
    token: str,
    text: str = _CARD_TEXT,
) -> Any:
    message = grpc_fixtures.request()
    message.artifact_ref.capability = token
    message.processing_policy.limits.max_input_bytes = 1024
    server, port = serve(_runtime(store, recognized, text), "127.0.0.1:0", 1)
    with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
        response = OcrServiceStub(channel).Recognize(message, timeout=5)
    server.stop(0)
    return response


class TestOcrServer:
    def test_round_trip_completes(self, store: str) -> None:
        response = _call(store, _VERIFIED, fixtures.issue())

        assert response.task_outcome == recognize_pb2.TASK_OUTCOME_COMPLETED
        assert response.result_completeness == (
            recognize_pb2.RESULT_COMPLETENESS_COMPLETE
        )
        snils = next(
            entry for entry in response.fields if entry.field_id == "snils"
        )
        assert snils.validations[0].status == (
            recognize_pb2.VALIDATION_STATUS_VALID
        )
        assert not response.diagnostics

    def test_refusal_is_partial_without_values(self, store: str) -> None:
        response = _call(store, _REFUSED, fixtures.issue())

        assert response.result_completeness == (
            recognize_pb2.RESULT_COMPLETENESS_PARTIAL
        )
        assert all(not entry.value for entry in response.fields)

    def test_bad_capability_is_technical(self, store: str) -> None:
        response = _call(store, _VERIFIED, fixtures.issue(task_id="task-2"))

        assert response.technical_code == (
            recognize_pb2.TECHNICAL_CODE_CAPABILITY_MISMATCH
        )

    def test_ambiguous_notice_is_subject_rejected(self, store: str) -> None:
        response = _call(store, _VERIFIED, fixtures.issue(), _NOTICE_TEXT)

        assert response.task_outcome == (
            recognize_pb2.TASK_OUTCOME_SUBJECT_REJECTED
        )
        assert response.subject_diagnostic == (
            recognize_pb2.SUBJECT_DIAGNOSTIC_FORM_AMBIGUOUS
        )
        assert all(not entry.value for entry in response.fields)

    def test_unknown_page_is_subject_rejected(self, store: str) -> None:
        response = _call(store, _VERIFIED, fixtures.issue(), "Справка")

        assert response.subject_diagnostic == (
            recognize_pb2.SUBJECT_DIAGNOSTIC_FORM_UNSUPPORTED
        )
