from __future__ import annotations

from types import MappingProxyType

import pytest

from sird_verification.corpus import (
    CorpusEvidenceStatus,
    CorpusManifest,
    CorpusSample,
    FieldLabel,
    PageProvenance,
    ProtectedTruthSet,
    SyntheticTransform,
    validate_manifest,
)

_SAMPLE_ID = "sample-1"
_SAMPLE_CHECKSUM = "sample-checksum"


def _page(source_id: str = "source-1") -> PageProvenance:
    return PageProvenance(
        page_id=f"{source_id}-page-0",
        source_id=source_id,
        raster_id=f"{source_id}-raster-0",
        rasterization_version="raster-v1",
        decoder_version="decoder-v1",
        checksum="page-checksum",
        visible_geometry={
            "width": TestCorpus.page_width,
            "height": TestCorpus.page_height,
        },
    )


def _manifest(*samples: CorpusSample) -> CorpusManifest:
    return CorpusManifest(
        corpus_version="corpus-v1",
        manifest_version="manifest-v1",
        comparison_policy_version="comparison-v1",
        samples=samples,
        partitions={
            "evaluation": tuple(sample.sample_id for sample in samples)
        },
        checksums={_SAMPLE_ID: _SAMPLE_CHECKSUM},
    )


def _sample(
    sample_id: str = _SAMPLE_ID,
    source_group_id: str = "group-1",
    physical_document_id: str | None = "physical-1",
) -> CorpusSample:
    fields = (
        FieldLabel(
            name="field-a",
            present=True,
            readability="readable",
            observed_text="observed-only",
            normalized_value="normalized-only",
        ),
    )
    return CorpusSample(
        sample_id=sample_id,
        source_group_id=source_group_id,
        physical_document_id=physical_document_id,
        pages=(_page(source_group_id),),
        fields=fields,
        partition="evaluation",
        checksum=_SAMPLE_CHECKSUM,
    )


def _truth(manifest: CorpusManifest) -> ProtectedTruthSet:
    return ProtectedTruthSet(
        truth_version="truth-v1",
        manifest_hash=manifest.manifest_hash,
        labels={_SAMPLE_ID: {"field-a": "protected-label"}},
    )


class TestCorpus:
    page_width = 100
    page_height = 80
    transform_angle = 2.5
    first_seed = 7
    different_seed = 8

    def test_variants_share_source_group(self) -> None:
        manifest = _manifest(
            _sample(),
            _sample(
                sample_id="sample-2",
                source_group_id="group-2",
            ),
        )

        evidence = validate_manifest(manifest, _truth(manifest))

        assert evidence.status is CorpusEvidenceStatus.FAIL
        assert "source group" in evidence.reason

    def test_manifest_is_truth_free_and_hashes(self) -> None:
        manifest = _manifest(_sample())

        working = manifest.working_manifest()
        serialized = repr(working)

        assert all(
            marker not in serialized
            for marker in (
                "protected-label",
                "observed-only",
                "normalized-only",
            )
        )
        assert "truth" not in working
        assert manifest.manifest_hash == _manifest(_sample()).manifest_hash
        assert isinstance(working, MappingProxyType)

    def test_synthetic_seed_reproducibility(self) -> None:
        first = SyntheticTransform(
            generator="generator-v1",
            template="template-a",
            parameters={"angle": self.transform_angle},
            seed=self.first_seed,
        )
        same = SyntheticTransform(
            generator="generator-v1",
            template="template-a",
            parameters={"angle": self.transform_angle},
            seed=self.first_seed,
        )
        different = SyntheticTransform(
            generator="generator-v1",
            template="template-a",
            parameters={"angle": self.transform_angle},
            seed=self.different_seed,
        )

        assert first.fingerprint == same.fingerprint
        assert first.fingerprint != different.fingerprint

    def test_checksum_mismatch_is_rejected(self) -> None:
        manifest = _manifest(_sample())

        evidence = validate_manifest(
            manifest,
            _truth(manifest),
            actual_checksums={_SAMPLE_ID: "not-the-declared-checksum"},
        )

        assert evidence.status is CorpusEvidenceStatus.FAIL
        assert "checksum" in evidence.reason

    def test_missing_truth_is_blocked(self) -> None:
        manifest = _manifest(_sample())

        evidence = validate_manifest(manifest)

        assert evidence.status is CorpusEvidenceStatus.BLOCKED
        assert not evidence.passed

    def test_matching_truth_passes(self) -> None:
        manifest = _manifest(_sample())

        evidence = validate_manifest(manifest, _truth(manifest))

        assert evidence.status is CorpusEvidenceStatus.PASS
        assert evidence.observed["manifest_hash"] == manifest.manifest_hash

    def test_value_checksum_mismatch_rejected(self) -> None:
        with pytest.raises(ValueError, match="checksum"):
            PageProvenance(
                page_id="page-1",
                source_id="source-1",
                checksum="declared",
                observed_checksum="observed",
            )
