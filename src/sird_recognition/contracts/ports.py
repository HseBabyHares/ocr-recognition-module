"""Transport-neutral ports for the stateless OCR computation."""

from typing import Protocol

from sird_recognition.contracts.stages import (
    ExecutionResult,
    ExecutionSpec,
    FormResolutionDecision,
    PreparedDocument,
    ProbeResult,
    StageContext,
)
from sird_recognition.contracts.text_observation import TextObservation


class PreparePort(Protocol):
    """Decode and prepare caller-authorized material."""

    def prepare(self, context: StageContext) -> PreparedDocument:
        """Return pages, provenance, diagnostics, and completeness."""


class ProbePort(Protocol):
    """Search prepared pages and report classifier evidence."""

    def probe(
        self, document: PreparedDocument, context: StageContext
    ) -> ProbeResult:
        """Return candidate evidence without selecting a profile."""


class ResolvePort(Protocol):
    """Resolve the subject form into an explicit decision."""

    def resolve(
        self, probe: ProbeResult, context: StageContext
    ) -> FormResolutionDecision:
        """Return the explicit form-resolution decision."""


class MaterialReaderPort(Protocol):
    """Read only caller-authorized material references."""

    def read(
        self,
        artifact_ref: str,
        *,
        expected_checksum: str,
    ) -> bytes:
        """Return verified bytes for one prepared artifact reference."""


class ExecuteProfilePort(Protocol):
    """Execute one classifier-selected profile."""

    def execute(
        self,
        document: PreparedDocument,
        specification: ExecutionSpec,
        context: StageContext,
        *,
        observations: tuple[TextObservation, ...] = (),
    ) -> ExecutionResult:
        """Return field results without durable task state."""


class TextReaderPort(Protocol):
    """Read text through one concrete adapter."""

    @property
    def adapter_id(self) -> str:
        """Return the stable adapter identifier."""

    def read(
        self,
        image: bytes,
        *,
        timeout_seconds: float,
        language: str,
        cpu_threads: int,
    ) -> TextObservation:
        """Return one raw observation or a typed reader failure."""


class TextReaderChainPort(Protocol):
    """Read text through an explicitly ordered adapter chain."""

    @property
    def reader_ids(self) -> tuple[str, ...]:
        """Return the configured adapter order."""

    def read(
        self,
        image: bytes,
        *,
        timeout_seconds: float,
        language: str,
        cpu_threads: int,
    ) -> TextObservation:
        """Return the first successful observation in configured order."""
