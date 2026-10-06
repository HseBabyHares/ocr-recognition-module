"""Runnable local SNILS upload app backed by system Tesseract."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from litestar import Litestar
from sird_recognition.candidate_extraction import GLiNERCandidateExtractor
from sird_recognition.snils_recognition import SnilsRecognitionService
from sird_recognition.tesseract_text_reader import TesseractTextReader

from sird_test_app import _checksums, _gliner, _tesseract
from sird_test_app.app import create_snils_app
from sird_test_app.jobs import InMemorySnilsJobService

READ_CHUNK_BYTES = _checksums.READ_CHUNK_BYTES
_REQUIRED_LANGUAGES = _tesseract.REQUIRED_LANGUAGES
_TESSDATA_DIRECTORIES = _tesseract._TESSDATA_DIRECTORIES
_REQUIRED_LANGUAGE_SET = frozenset(_REQUIRED_LANGUAGES)
_sha256_file = _checksums.sha256_file
_verify_allowlisted_checksum = _checksums.verify_allowlisted_checksum
_tessdata_checksum = _checksums.tessdata_checksum
_available_languages = _tesseract.available_languages
_tessdata_directory = _tesseract.tessdata_directory
_load_fixed_tokenizer = _gliner._load_fixed_tokenizer
_load_gliner_model = _gliner.load_gliner_model

GLINER_THRESHOLD = 0.35
GLINER_MAX_TEXT_LENGTH = 32000
GLINER_MAX_CANDIDATES = 64


def _load_candidate_extractor() -> GLiNERCandidateExtractor | None:
    """Load the optional local GLiNER model only for the test profile."""
    if os.environ.get("SIRD_GLINER_ENABLED") != "1":
        return None
    configured = os.environ.get("SIRD_GLINER_MODEL_DIR")
    if not configured:
        raise RuntimeError(
            "SIRD_GLINER_MODEL_DIR is required when GLiNER is enabled"
        )
    model_dir = Path(configured)
    if not model_dir.is_dir():
        raise RuntimeError("SIRD_GLINER_MODEL_DIR is unavailable")
    try:
        model = _load_gliner_model(model_dir)
    except Exception as caught_error:
        raise RuntimeError(
            "GLiNER local model is unavailable"
        ) from caught_error
    return GLiNERCandidateExtractor(
        model=model,
        model_id=str(model_dir),
        model_revision="local",
        threshold=GLINER_THRESHOLD,
        max_text_length=GLINER_MAX_TEXT_LENGTH,
        max_candidates=GLINER_MAX_CANDIDATES,
    )


def _build_service(
    executable: str,
    tessdata: Path,
) -> SnilsRecognitionService:
    implementation_checksum = _sha256_file(Path(executable))
    tessdata_checksum = _tessdata_checksum(tessdata)
    _verify_allowlisted_checksum(
        "SIRD_TESSERACT_SHA256", implementation_checksum
    )
    _verify_allowlisted_checksum("SIRD_TESSDATA_SHA256", tessdata_checksum)
    reader = TesseractTextReader(
        implementation_checksum=implementation_checksum,
        tessdata_checksum=tessdata_checksum,
    )
    return SnilsRecognitionService(
        reader,
        candidate_extractor=_load_candidate_extractor(),
    )


def create_local_snils_app() -> Litestar:
    """Create the local upload app without network or model downloads."""
    executable = shutil.which("tesseract")
    if executable is None:
        raise RuntimeError("Tesseract executable is required")
    if not _available_languages(executable) >= _REQUIRED_LANGUAGE_SET:
        raise RuntimeError("Tesseract rus and eng languages are required")
    tessdata = _tessdata_directory()
    service = _build_service(executable, tessdata)
    return create_snils_app(InMemorySnilsJobService(service))
