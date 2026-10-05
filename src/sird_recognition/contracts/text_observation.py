"""Explicit OCR observation and adapter provenance contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdapterDescriptor:
    """Applied adapter identity and declared implementation capabilities."""

    adapter_id: str
    adapter_version: str
    implementation_checksum: str
    model_revision: str | None
    device: str
    input_kinds: tuple[str, ...]
    output_capabilities: frozenset[str]
    configuration: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class TextRegion:
    """One actual OCR word region and its reported confidence."""

    left: int
    top: int
    width: int
    height: int
    line_number: int
    text: str
    confidence: float | None


@dataclass(frozen=True, slots=True)
class TextObservation:
    """One OCR observation and only capabilities actually provided."""

    raw_text: str
    adapter_id: str
    adapter_version: str
    regions: tuple[TextRegion, ...] | None = None
    word_scores: tuple[float, ...] | None = None
    character_alternatives: tuple[tuple[str, ...], ...] | None = None
    descriptor: AdapterDescriptor | None = None
    language: str | None = None
    skipped_reader_ids: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    @property
    def capabilities(self) -> frozenset[str]:
        """Return capabilities represented by non-synthetic output."""
        capabilities = {"text"}
        if self.regions is not None:
            capabilities.add("text_regions")
        if self.word_scores is not None:
            capabilities.add("word_scores")
        if self.character_alternatives is not None:
            capabilities.add("character_alternatives")
        return frozenset(capabilities)
