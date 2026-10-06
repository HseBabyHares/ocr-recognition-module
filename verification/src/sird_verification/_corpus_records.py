"""Compatibility facade for immutable corpus record types."""

from __future__ import annotations

from sird_verification import _corpus_collection_records as _collections
from sird_verification import _corpus_record_primitives as _primitives

CorpusEvidence = _collections.CorpusEvidence
CorpusManifest = _collections.CorpusManifest
CorpusSample = _collections.CorpusSample
FieldLabel = _primitives.FieldLabel
PageProvenance = _primitives.PageProvenance
ProtectedTruthSet = _collections.ProtectedTruthSet
SyntheticTransform = _primitives.SyntheticTransform
