from __future__ import annotations

import pytest

from sird_test_app.local_snils import (
    _load_candidate_extractor,
    _verify_allowlisted_checksum,
)

TESSERACT_CHECKSUM_ENV = "SIRD_TESSERACT_SHA256"
TESSDATA_CHECKSUM_ENV = "SIRD_TESSDATA_SHA256"
EXPECTED_CHECKSUM = "expected"
OBSERVED_CHECKSUM = "observed"
GLINER_ENABLED_ENV = "SIRD_GLINER_ENABLED"
GLINER_MODEL_DIR_ENV = "SIRD_GLINER_MODEL_DIR"
MISSING_MODEL_DIR = "/does/not/exist"
MATCHING_CHECKSUM = "abc123"


def test_allowlist_accepts_matching_value(monkeypatch) -> None:
    monkeypatch.setenv(TESSERACT_CHECKSUM_ENV, MATCHING_CHECKSUM)

    _verify_allowlisted_checksum(TESSERACT_CHECKSUM_ENV, MATCHING_CHECKSUM)


def test_allowlisted_checksum_rejects_mismatch(monkeypatch) -> None:
    monkeypatch.setenv(TESSDATA_CHECKSUM_ENV, EXPECTED_CHECKSUM)

    with pytest.raises(RuntimeError, match=TESSDATA_CHECKSUM_ENV):
        _verify_allowlisted_checksum(
            TESSDATA_CHECKSUM_ENV,
            OBSERVED_CHECKSUM,
        )


def test_gliner_loader_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv(GLINER_ENABLED_ENV, raising=False)
    monkeypatch.setenv(GLINER_MODEL_DIR_ENV, MISSING_MODEL_DIR)
    assert _load_candidate_extractor() is None
