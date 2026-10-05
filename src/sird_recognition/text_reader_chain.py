"""Explicit OCR text-reader ordering without hidden fallback."""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import replace

from sird_recognition.contracts.ports import (
    TextReaderChainPort,
    TextReaderPort,
)
from sird_recognition.contracts.text_observation import TextObservation
from sird_recognition.text_reader_errors import (
    TextReaderLimitError,
    TextReaderUnavailableError,
)


def _attempted_readers(reader_ids: list[str]) -> str:
    return ", ".join(reader_ids) or "none"


def _unavailable_message(reader_ids: list[str]) -> str:
    return (
        "no configured text reader is available; "
        f"attempted={_attempted_readers(reader_ids)}"
    )


def _with_skipped_readers(
    observation: TextObservation,
    skipped_reader_ids: list[str],
) -> TextObservation:
    return replace(
        observation,
        skipped_reader_ids=tuple(skipped_reader_ids),
        diagnostics=observation.diagnostics
        + tuple(
            f"reader_unavailable:{reader_id}"
            for reader_id in skipped_reader_ids
        ),
    )


class TextReaderChain(TextReaderChainPort):
    """Try only the reader order supplied by the profile."""

    def __init__(self, readers: Sequence[TextReaderPort]) -> None:
        if not readers:
            raise ValueError("at least one text reader is required")
        self._readers = tuple(readers)

    @property
    def reader_ids(self) -> tuple[str, ...]:
        """Return the configured order for applied-execution evidence."""

        return tuple(reader.adapter_id for reader in self._readers)

    def read(
        self,
        image: bytes,
        *,
        timeout_seconds: float,
        language: str,
        cpu_threads: int,
    ) -> TextObservation:
        """Return the first successful observation in configured order."""
        deadline = time.monotonic() + timeout_seconds
        unavailable: list[str] = []
        for reader in self._readers:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TextReaderLimitError(
                    "text-reader deadline was exhausted"
                )
            try:
                observation = reader.read(
                    image,
                    timeout_seconds=remaining,
                    language=language,
                    cpu_threads=cpu_threads,
                )
            except TextReaderUnavailableError:
                unavailable.append(reader.adapter_id)
                continue
            return _with_skipped_readers(observation, unavailable)
        raise TextReaderUnavailableError(_unavailable_message(unavailable))


def create_reader_chain(
    readers: Sequence[TextReaderPort],
) -> TextReaderChain:
    """Create a chain in the exact order declared by the caller."""

    return TextReaderChain(readers)


def create_tesseract_first_chain(
    *,
    implementation_checksum: str,
    tessdata_checksum: str,
    fallbacks: Sequence[TextReaderPort] = (),
) -> TextReaderChain:
    """Create an explicitly requested project-local Tesseract chain."""
    from sird_recognition.tesseract_text_reader import TesseractTextReader

    return create_reader_chain(
        (
            TesseractTextReader(
                implementation_checksum=implementation_checksum,
                tessdata_checksum=tessdata_checksum,
            ),
            *tuple(fallbacks),
        )
    )
