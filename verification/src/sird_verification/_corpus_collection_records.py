"""Collection records for corpus samples, manifests, and truth."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from sird_verification._corpus_enums import CorpusEvidenceStatus
from sird_verification._corpus_record_primitives import (
    FieldLabel,
    PageProvenance,
    SyntheticTransform,
)
from sird_verification._corpus_serialization import (
    digest,
    freeze,
    jsonable,
    non_empty,
)

_METADATA_KEY = "metadata"

# Aliases keep the public record annotations readable without changing them.
type FieldValues = Mapping[str, str | None]
type TruthLabels = Mapping[str, FieldValues]


@dataclass(frozen=True, slots=True)
class CorpusSample:
    """One physical source or a deterministic variant of that source."""

    sample_id: str
    source_group_id: str
    pages: tuple[PageProvenance, ...]
    fields: tuple[FieldLabel, ...] = ()
    physical_document_id: str | None = None
    synthetic_transform: SyntheticTransform | None = None
    partition: str = ""
    checksum: str = ""
    observed_checksum: str | None = None
    metadata: Mapping[str, Any] = MappingProxyType({})

    def __post_init__(self) -> None:
        non_empty(self.sample_id, "sample_id")
        non_empty(self.source_group_id, "source_group_id")
        if not self.pages:
            raise ValueError("a sample must contain at least one page")
        self._validate_checksum()
        pages = tuple(self.pages)
        fields = tuple(self.fields)
        self._validate_member_names(pages, fields)
        object.__setattr__(self, "pages", pages)
        object.__setattr__(self, "fields", fields)
        object.__setattr__(self, _METADATA_KEY, freeze(self.metadata))

    def as_dict(self) -> dict[str, Any]:
        """Return the working representation, with no reference values."""
        return {
            "sample_id": self.sample_id,
            "fields": [
                field.as_dict(include_observation=False)
                for field in self.fields
            ],
            "physical_document_id": self.physical_document_id,
            "pages": [page.as_dict() for page in self.pages],
            "synthetic_transform": (
                self.synthetic_transform.as_dict()
                if self.synthetic_transform
                else None
            ),
            "partition": self.partition,
            "checksum": self.checksum,
            _METADATA_KEY: jsonable(self.metadata),
        }

    def _validate_checksum(self) -> None:
        if (
            self.checksum
            and self.observed_checksum
            and self.checksum != self.observed_checksum
        ):
            raise ValueError(
                "sample checksum does not match observed checksum"
            )

    def _validate_member_names(
        self,
        pages: tuple[PageProvenance, ...],
        fields: tuple[FieldLabel, ...],
    ) -> None:
        if len({page.page_id for page in pages}) != len(pages):
            raise ValueError("page IDs must be unique within a sample")
        if len({field.name for field in fields}) != len(fields):
            raise ValueError("field names must be unique within a sample")


@dataclass(frozen=True, slots=True)
class CorpusManifest:
    """Versioned, truth-free corpus description sent to working OCR."""

    corpus_version: str
    manifest_version: str
    comparison_policy_version: str
    samples: tuple[CorpusSample, ...]
    partitions: Mapping[str, tuple[str, ...]] = MappingProxyType({})
    checksums: Mapping[str, str] = MappingProxyType({})
    metadata: Mapping[str, Any] = MappingProxyType({})

    def __post_init__(self) -> None:
        non_empty(self.corpus_version, "corpus_version")
        non_empty(self.manifest_version, "manifest_version")
        non_empty(
            self.comparison_policy_version,
            "comparison_policy_version",
        )
        samples = tuple(self.samples)
        if not samples:
            raise ValueError("manifest must contain at least one sample")
        if len({sample.sample_id for sample in samples}) != len(samples):
            raise ValueError("sample IDs must be unique")
        object.__setattr__(self, "samples", samples)
        object.__setattr__(self, "partitions", freeze(self.partitions))
        object.__setattr__(self, "checksums", freeze(self.checksums))
        object.__setattr__(self, _METADATA_KEY, freeze(self.metadata))

    def working_manifest(self) -> Mapping[str, Any]:
        """Return an immutable manifest that contains no protected labels."""
        payload = {
            "corpus_version": self.corpus_version,
            "manifest_version": self.manifest_version,
            "comparison_policy_version": self.comparison_policy_version,
            "samples": [sample.as_dict() for sample in self.samples],
            "partitions": jsonable(self.partitions),
            "checksums": jsonable(self.checksums),
            _METADATA_KEY: jsonable(self.metadata),
        }
        return freeze(payload)

    @property
    def manifest_hash(self) -> str:
        """Return the deterministic hash of the truth-free manifest."""
        return digest(self.working_manifest())


@dataclass(frozen=True, slots=True)
class ProtectedTruthSet:
    """Reference labels held outside the working manifest."""

    truth_version: str
    manifest_hash: str
    labels: TruthLabels
    metadata: Mapping[str, Any] = MappingProxyType({})

    def __post_init__(self) -> None:
        non_empty(self.truth_version, "truth_version")
        non_empty(self.manifest_hash, "manifest_hash")
        labels = {
            str(sample_id): MappingProxyType(dict(field_values))
            for sample_id, field_values in self.labels.items()
        }
        object.__setattr__(self, "labels", MappingProxyType(labels))
        object.__setattr__(self, _METADATA_KEY, freeze(self.metadata))

    def label_for(self, sample_id: str, field_name: str) -> str | None:
        """Read one protected value for evaluator code."""
        return self.labels[sample_id][field_name]


@dataclass(frozen=True, slots=True)
class CorpusEvidence:
    """Bounded result from manifest and truth validation."""

    status: CorpusEvidenceStatus
    reason: str
    observed: Mapping[str, Any] = MappingProxyType({})

    def __post_init__(self) -> None:
        non_empty(self.reason, "reason")
        object.__setattr__(
            self,
            "observed",
            MappingProxyType(dict(self.observed)),
        )

    @property
    def passed(self) -> bool:
        """Whether validation passed."""
        return self.status is CorpusEvidenceStatus.PASS

    @property
    def blocked(self) -> bool:
        """Whether validation is blocked by missing prerequisites."""
        return self.status is CorpusEvidenceStatus.BLOCKED
