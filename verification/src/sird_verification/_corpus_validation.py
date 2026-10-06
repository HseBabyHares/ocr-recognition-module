"""Validation routines for corpus manifests and protected truth."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from sird_verification._corpus_enums import CorpusEvidenceStatus
from sird_verification._corpus_records import CorpusEvidence

if TYPE_CHECKING:
    from sird_verification._corpus_records import (
        CorpusManifest,
        ProtectedTruthSet,
    )


def _check_sample_checksums(manifest: CorpusManifest) -> CorpusEvidence | None:
    expected = dict(manifest.checksums)
    for sample in manifest.samples:
        declared = expected.get(sample.sample_id)
        if declared is not None and sample.checksum != declared:
            return CorpusEvidence(
                CorpusEvidenceStatus.FAIL,
                f"checksum mismatch for {sample.sample_id}",
            )
    return None


def _check_source_groups(manifest: CorpusManifest) -> CorpusEvidence | None:
    sample_groups: dict[str, str] = {}
    physical_groups: dict[str, str] = {}
    for sample in manifest.samples:
        if sample.physical_document_id:
            previous = physical_groups.setdefault(
                sample.physical_document_id,
                sample.source_group_id,
            )
            if previous != sample.source_group_id:
                return CorpusEvidence(
                    CorpusEvidenceStatus.FAIL,
                    "physical document variants must share a source group",
                )
        for page in sample.pages:
            previous = sample_groups.setdefault(
                page.source_id,
                sample.source_group_id,
            )
            if previous != sample.source_group_id:
                return CorpusEvidence(
                    CorpusEvidenceStatus.FAIL,
                    "page source variants must share a source group",
                )
    return None


def _check_partitions(manifest: CorpusManifest) -> CorpusEvidence | None:
    partition_ids = [
        sample_id
        for members in manifest.partitions.values()
        for sample_id in members
    ]
    sample_ids = {sample.sample_id for sample in manifest.samples}
    if manifest.partitions and set(partition_ids) != sample_ids:
        return CorpusEvidence(
            CorpusEvidenceStatus.FAIL,
            "partitions must include each sample exactly once",
        )
    if len(partition_ids) != len(set(partition_ids)):
        return CorpusEvidence(
            CorpusEvidenceStatus.FAIL,
            "a sample must occur in one partition only",
        )
    return None


def _check_actual_checksums(
    manifest: CorpusManifest,
    actual_checksums: Mapping[str, str] | None,
) -> CorpusEvidence | None:
    if not actual_checksums:
        return None
    expected = dict(manifest.checksums)
    for identity, checksum in actual_checksums.items():
        declared = expected.get(identity)
        if declared is not None and declared != checksum:
            return CorpusEvidence(
                CorpusEvidenceStatus.FAIL,
                f"checksum mismatch for {identity}",
            )
    return None


def _check_truth(
    manifest: CorpusManifest,
    truth: ProtectedTruthSet | None,
) -> CorpusEvidence | None:
    if truth is None:
        return CorpusEvidence(
            CorpusEvidenceStatus.BLOCKED,
            "protected truth is required for corpus validation",
        )
    if truth.manifest_hash != manifest.manifest_hash:
        return CorpusEvidence(
            CorpusEvidenceStatus.FAIL,
            "protected truth does not match manifest hash",
        )
    sample_ids = {sample.sample_id for sample in manifest.samples}
    if set(truth.labels) != sample_ids:
        return CorpusEvidence(
            CorpusEvidenceStatus.FAIL,
            "protected truth labels do not match manifest samples",
        )
    return None


def _validate(
    manifest: CorpusManifest,
    truth: ProtectedTruthSet | None,
    actual_checksums: Mapping[str, str] | None,
) -> CorpusEvidence:
    for evidence in (
        _check_sample_checksums(manifest),
        _check_source_groups(manifest),
        _check_partitions(manifest),
        _check_actual_checksums(manifest, actual_checksums),
        _check_truth(manifest, truth),
    ):
        if evidence is not None:
            return evidence
    return CorpusEvidence(
        CorpusEvidenceStatus.PASS,
        "manifest and protected truth are compatible",
        {
            "sample_count": len(manifest.samples),
            "manifest_hash": manifest.manifest_hash,
        },
    )


def validate_manifest(
    manifest: CorpusManifest,
    truth: ProtectedTruthSet | None = None,
    *,
    actual_checksums: Mapping[str, str] | None = None,
) -> CorpusEvidence:
    """Validate provenance, partitions, checksums, and truth separation."""
    try:
        return _validate(manifest, truth, actual_checksums)
    except (TypeError, ValueError, KeyError) as error:
        return CorpusEvidence(CorpusEvidenceStatus.ERROR, str(error))
