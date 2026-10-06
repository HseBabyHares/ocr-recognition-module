"""Versioned OCR corpus manifests and protected evaluation truth.

The manifest is the public input to OCR execution.  Reference values stay in
``ProtectedTruthSet`` and are only intended for an independent evaluator.
"""

from __future__ import annotations

from sird_verification import _corpus_enums as _enums
from sird_verification import _corpus_records as _records
from sird_verification import _corpus_validation as _validation

CorpusEvidenceStatus = _enums.CorpusEvidenceStatus
CorpusStatus = _enums.CorpusStatus
FieldPresence = _enums.FieldPresence
FieldReadability = _enums.FieldReadability
CorpusEvidence = _records.CorpusEvidence
CorpusManifest = _records.CorpusManifest
CorpusSample = _records.CorpusSample
FieldLabel = _records.FieldLabel
PageProvenance = _records.PageProvenance
ProtectedTruthSet = _records.ProtectedTruthSet
SyntheticTransform = _records.SyntheticTransform
validate_manifest = _validation.validate_manifest
