from __future__ import annotations

import pytest

from sird_recognition.codes import TechnicalCode
from sird_recognition.runtime import RecognitionError
from tests import _grpc_fixtures as grpc_fixtures
from tests import _ocr_fixtures as fixtures

_DENIED = TechnicalCode.AUTHORIZATION_FAILED


class TestCapabilityVerifier:
    def test_process_token_verifies(self) -> None:
        claims = fixtures.VERIFIER.verify(
            fixtures.issue(),
            task_id=grpc_fixtures.TASK_ID,
            request_id=grpc_fixtures.REQUEST_ID,
        )

        assert claims.object_id == fixtures.OBJECT_ID
        assert claims.size == len(fixtures.IMAGE)

    @pytest.mark.parametrize(
        ("token", "task_id", "code"),
        [
            (fixtures.tampered(), grpc_fixtures.TASK_ID, _DENIED),
            (fixtures.issue(audience="other"), grpc_fixtures.TASK_ID, _DENIED),
            (
                fixtures.issue(expires_at="2026-10-13T12:00:00Z"),
                grpc_fixtures.TASK_ID,
                _DENIED,
            ),
            (fixtures.issue(size=True), grpc_fixtures.TASK_ID, _DENIED),
            ("v2.e30.e30", grpc_fixtures.TASK_ID, _DENIED),
            (fixtures.issue(), "task-2", TechnicalCode.CAPABILITY_MISMATCH),
        ],
    )
    def test_token_rejections(
        self, token: str, task_id: str, code: TechnicalCode
    ) -> None:
        with pytest.raises(RecognitionError) as rejected:
            fixtures.VERIFIER.verify(
                token, task_id=task_id, request_id=grpc_fixtures.REQUEST_ID
            )

        assert rejected.value.code is code
