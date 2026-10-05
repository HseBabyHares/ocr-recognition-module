"""Process helpers for the project-local Tesseract adapter."""

from __future__ import annotations

import subprocess

from sird_recognition.text_reader_errors import (
    TextReaderExecutionError,
    TextReaderLimitError,
    TextReaderUnavailableError,
)


def decode_output(output: object) -> str:
    if not isinstance(output, bytes):
        raise TextReaderExecutionError(
            "tesseract returned a non-byte output payload"
        )
    try:
        return output.decode("utf-8")
    except UnicodeDecodeError as error:
        raise TextReaderExecutionError(
            "tesseract returned non-UTF-8 text"
        ) from error


def process_error(error: Exception) -> Exception:
    if isinstance(error, FileNotFoundError):
        return TextReaderUnavailableError("OCR executable is unavailable")
    if isinstance(error, subprocess.TimeoutExpired):
        return TextReaderLimitError(
            "tesseract execution exceeded its time limit"
        )
    if isinstance(error, OSError):
        return TextReaderUnavailableError("OCR process could not be started")
    return TextReaderExecutionError("tesseract execution failed")


def language_unavailable(stderr: str) -> bool:
    lowered_stderr = stderr.lower()
    return "failed loading language" in lowered_stderr or (
        "error opening data file" in lowered_stderr
    )


def check_completed(return_code: int, stderr: str) -> None:
    if return_code == 0:
        return
    if language_unavailable(stderr):
        raise TextReaderUnavailableError(
            "requested Tesseract language data is unavailable"
        )
    raise TextReaderExecutionError("tesseract returned a non-zero exit status")
