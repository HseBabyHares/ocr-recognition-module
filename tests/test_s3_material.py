from __future__ import annotations

import hashlib

import pytest

from sird_recognition.codes import TechnicalCode
from sird_recognition.runtime import RecognitionError
from tests import _ocr_fixtures as fixtures
from tests._object_store import ObjectStore, reader


class TestS3MaterialReader:
    def test_signed_read(self, store: str) -> None:
        body = reader(store).read(
            fixtures.OBJECT_KEY, expected_checksum=fixtures.CHECKSUM
        )

        assert body == fixtures.IMAGE
        assert ObjectStore.authorization.startswith(
            "AWS4-HMAC-SHA256 Credential=access/"
        )

    def test_checksum_mismatch(self, store: str) -> None:
        other = hashlib.sha256(b"other").hexdigest()

        with pytest.raises(RecognitionError) as mismatch:
            reader(store).read(fixtures.OBJECT_KEY, expected_checksum=other)

        assert mismatch.value.code is TechnicalCode.CAPABILITY_MISMATCH

    def test_missing_object_is_final(self, store: str) -> None:
        with pytest.raises(RecognitionError) as missing:
            reader(store).read(
                "objects/2", expected_checksum=fixtures.CHECKSUM
            )

        assert missing.value.code is TechnicalCode.MATERIAL_UNAVAILABLE
        assert not missing.value.retryable
