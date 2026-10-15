"""Compute and pin the Tesseract executable and language data checksums."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

_LANGUAGES = ("eng", "rus")
_TESSDATA_DIRECTORIES = (
    "/usr/share/tesseract-ocr/5/tessdata",
    "/usr/share/tesseract-ocr/4.00/tessdata",
    "/usr/share/tessdata",
)


def tesseract_checksums() -> tuple[str, str]:
    """Return the executable and the tessdata checksums, failing closed."""
    executable = shutil.which("tesseract")
    if executable is None:
        raise RuntimeError("Tesseract executable is required")
    tessdata = _tessdata()
    # Same digest as the test app: sha256 over the sorted per-file hex.
    combined = hashlib.sha256(
        b"".join(
            _sha256(tessdata / f"{language}.traineddata").encode()
            for language in _LANGUAGES
        )
    ).hexdigest()
    return (
        _pinned("SIRD_TESSERACT_SHA256", _sha256(Path(executable))),
        _pinned("SIRD_TESSDATA_SHA256", combined),
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pinned(name: str, actual: str) -> str:
    expected = os.environ.get(name)
    if expected is not None and expected.strip().lower() != actual:
        raise RuntimeError(f"{name} does not match the runtime checksum")
    return actual


def _tessdata() -> Path:
    prefix = os.environ.get("TESSDATA_PREFIX")
    configured = (Path(prefix), Path(prefix) / "tessdata") if prefix else ()
    candidates = (*configured, *map(Path, _TESSDATA_DIRECTORIES))
    for candidate in candidates:
        if all(
            (candidate / f"{language}.traineddata").is_file()
            for language in _LANGUAGES
        ):
            return candidate
    raise RuntimeError("Tesseract rus and eng language data are required")
