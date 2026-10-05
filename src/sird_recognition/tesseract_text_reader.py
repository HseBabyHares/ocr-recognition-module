"""Project-local Tesseract text-reader adapter."""

from __future__ import annotations

import math
import os
import subprocess
from collections.abc import Callable
from typing import Any

from sird_recognition._tesseract_support import (
    check_completed as _check_completed,
)
from sird_recognition._tesseract_support import (
    decode_output as _decode_output,
)
from sird_recognition._tesseract_support import (
    process_error as _process_error,
)
from sird_recognition._tesseract_tsv import parse_tsv
from sird_recognition.contracts.text_observation import (
    AdapterDescriptor,
    TextObservation,
    TextRegion,
)

_MAX_PAGE_SEGMENTATION_MODE = 13
_DEFAULT_PAGE_SEGMENTATION_MODE = 6


def _require_text(text: str, name: str) -> str:
    if not text.strip():
        raise ValueError(f"{name} must be non-empty")
    return text


def _require_page_segmentation_mode(mode: int) -> int:
    if mode < 0 or mode > _MAX_PAGE_SEGMENTATION_MODE:
        raise ValueError("page_segmentation_mode must be between 0 and 13")
    return mode


def _require_timeout(timeout: float) -> float:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout_seconds must be finite and positive")
    return timeout


def _require_image(image: bytes) -> bytes:
    if not isinstance(image, bytes) or not image:
        raise ValueError("image must be non-empty bytes")
    return image


def _require_cpu_threads(cpu_threads: int) -> int:
    if not isinstance(cpu_threads, int) or cpu_threads <= 0:
        raise ValueError("cpu_threads must be a positive integer")
    return cpu_threads


class _TsvParser:
    """Parse the stable subset of Tesseract TSV output."""

    @classmethod
    def parse(
        cls,
        output: object,
    ) -> tuple[str, tuple[TextRegion, ...], tuple[float, ...]]:
        return parse_tsv(output)


class TesseractTextReader:
    """Read bounded raster bytes through explicitly configured Tesseract."""

    def __init__(
        self,
        *,
        page_segmentation_mode: int = _DEFAULT_PAGE_SEGMENTATION_MODE,
        implementation_checksum: str,
        tessdata_checksum: str,
        runner: Callable[..., Any] = subprocess.run,
    ) -> None:
        self._page_segmentation_mode = _require_page_segmentation_mode(
            page_segmentation_mode
        )
        self._implementation_checksum = _require_text(
            implementation_checksum, "implementation_checksum"
        )
        self._tessdata_checksum = _require_text(
            tessdata_checksum, "tessdata_checksum"
        )
        self._runner = runner

    @property
    def adapter_id(self) -> str:
        """Return the stable adapter identifier."""

        return "tesseract"

    def read(
        self,
        image: bytes,
        *,
        timeout_seconds: float,
        language: str,
        cpu_threads: int,
    ) -> TextObservation:
        """Read TSV output and preserve actual regions and word scores."""
        image = _require_image(image)
        language = _require_text(language, "language")
        timeout_seconds = _require_timeout(timeout_seconds)
        cpu_threads = _require_cpu_threads(cpu_threads)
        completed = self._run(image, timeout_seconds, language, cpu_threads)
        return self._observation(completed, language, cpu_threads)

    def _run(
        self,
        image: bytes,
        timeout_seconds: float,
        language: str,
        cpu_threads: int,
    ) -> Any:
        command = (
            "tesseract",
            "stdin",
            "stdout",
            "--psm",
            str(self._page_segmentation_mode),
            "-l",
            language,
            "tsv",
        )
        environment = os.environ.copy()
        environment["OMP_THREAD_LIMIT"] = str(cpu_threads)
        try:
            return self._runner(
                command,
                input=image,
                capture_output=True,
                check=False,
                timeout=timeout_seconds,
                env=environment,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            raise _process_error(exc) from exc

    def _observation(
        self,
        completed: Any,
        language: str,
        cpu_threads: int,
    ) -> TextObservation:
        stderr = _decode_output(completed.stderr)
        _check_completed(completed.returncode, stderr)
        raw_text, regions, scores = _TsvParser.parse(completed.stdout)
        return TextObservation(
            raw_text=raw_text,
            adapter_id=self.adapter_id,
            adapter_version="tesseract-cli-v1",
            regions=regions,
            word_scores=scores,
            descriptor=self._descriptor(language, cpu_threads),
            language=language,
        )

    def _descriptor(
        self, language: str, cpu_threads: int
    ) -> AdapterDescriptor:
        return AdapterDescriptor(
            adapter_id=self.adapter_id,
            adapter_version="tesseract-cli-v1",
            implementation_checksum=self._implementation_checksum,
            model_revision=self._tessdata_checksum,
            device="cpu",
            input_kinds=("raster_bytes",),
            output_capabilities=frozenset(
                ("text", "text_regions", "word_scores")
            ),
            configuration={
                "language": language,
                "cpu_threads": cpu_threads,
                "page_segmentation_mode": self._page_segmentation_mode,
            },
        )
