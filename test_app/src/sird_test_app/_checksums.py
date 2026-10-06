"""Checksum helpers for the local Tesseract profile."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

READ_CHUNK_BYTES = 1024 * 1024
_REQUIRED_LANGUAGES = ("eng", "rus")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as checksum_stream:
        for chunk in iter(checksum_stream.read, b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_allowlisted_checksum(
    environment_variable: str, actual: str
) -> None:
    expected = os.environ.get(environment_variable)
    if expected is None:
        return
    normalized = expected.strip().lower()
    if normalized != actual:
        raise RuntimeError(
            f"{environment_variable} does not match the runtime checksum"
        )


def tessdata_checksum(tessdata: Path) -> str:
    digest = hashlib.sha256()
    for language in sorted(_REQUIRED_LANGUAGES):
        digest.update(
            sha256_file(tessdata / f"{language}.traineddata").encode()
        )
    return digest.hexdigest()
