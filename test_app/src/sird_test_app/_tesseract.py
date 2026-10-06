"""Tesseract executable and language-data discovery helpers."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

TESSERACT_LANGUAGE_LIST_TIMEOUT_SECONDS = 5
REQUIRED_LANGUAGES = ("eng", "rus")

_TESSDATA_DIRECTORIES = (
    Path("/usr/share/tesseract-ocr/5/tessdata"),
    Path("/usr/share/tesseract-ocr/4.00/tessdata"),
    Path("/usr/share/tessdata"),
)


def available_languages(executable: str) -> set[str]:
    completed = subprocess.run(
        (executable, "--list-langs"),
        capture_output=True,
        check=False,
        text=True,
        timeout=TESSERACT_LANGUAGE_LIST_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise RuntimeError("Tesseract language discovery failed")
    return {
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip() and not line.startswith("List of available languages")
    }


def tessdata_directory() -> Path:
    prefix = os.environ.get("TESSDATA_PREFIX")
    candidates: list[Path] = []
    if prefix:
        configured = Path(prefix)
        candidates.extend((configured, configured / "tessdata"))
    candidates.extend(_TESSDATA_DIRECTORIES)
    for candidate in candidates:
        if all(
            (candidate / f"{language}.traineddata").is_file()
            for language in REQUIRED_LANGUAGES
        ):
            return candidate
    raise RuntimeError("Tesseract rus and eng language data are required")
