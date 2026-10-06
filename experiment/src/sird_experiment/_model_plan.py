"""Immutable experiment variants and deterministic execution plans."""

from __future__ import annotations

import random
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, cast

from sird_experiment._model_enums import ExperimentMode
from sird_experiment._model_safety import _check_safe, _text
from sird_experiment._model_serialization import _digest, _freeze
from sird_experiment._plan_freezing import (
    _freeze_identifiers,
    _freeze_metadata,
)
from sird_experiment._plan_pair_helpers import (
    finalize_pairs as _finalize_pairs,
)
from sird_experiment._plan_validation import _prepare_plan


def _is_non_empty_name(name: str) -> bool:
    return isinstance(name, str) and bool(name.strip())


def _has_non_empty_names(names: tuple[str, ...]) -> bool:
    return all(_is_non_empty_name(name) for name in names)


def _expanded_pairs(
    pair_order: tuple[tuple[str, str, int], ...] | None,
) -> tuple[tuple[str, str, int], ...]:
    return cast(tuple[tuple[str, str, int], ...], pair_order)


def _validate_substitution_names(
    assistance: tuple[str, ...],
    test_doubles: tuple[str, ...],
) -> None:
    substitution_names = assistance + test_doubles
    if not _has_non_empty_names(substitution_names):
        raise ValueError(
            "assistance and test_doubles must contain non-empty names"
        )


_MODEL_MODULE = "sird_experiment.models"
_PROVENANCE_FIELD = "provenance"


@dataclass(frozen=True, slots=True)
class ExperimentVariant:
    """One fully declared implementation profile, without protected truth."""

    __module__ = _MODEL_MODULE

    variant_id: str
    specification: Mapping[str, Any] = field(default_factory=dict)
    base_variant: str | None = None
    assistance: tuple[str, ...] = ()
    test_doubles: tuple[str, ...] = ()
    code_checksum: str | None = None
    weights_checksum: str | None = None
    provenance: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _text(self.variant_id, "variant_id")
        _check_safe(self.specification)
        _check_safe(self.provenance)
        object.__setattr__(
            self, "specification", _freeze(dict(self.specification))
        )
        object.__setattr__(
            self, _PROVENANCE_FIELD, _freeze(dict(self.provenance))
        )
        object.__setattr__(self, "assistance", tuple(self.assistance))
        object.__setattr__(self, "test_doubles", tuple(self.test_doubles))
        _validate_substitution_names(self.assistance, self.test_doubles)

    @property
    def resolved_spec_hash(self) -> str:
        return _digest(self.to_mapping())

    @property
    def substitutions_declared(self) -> bool:
        return bool(self.assistance or self.test_doubles)

    def to_mapping(self) -> Mapping[str, Any]:
        return {
            "variant_id": self.variant_id,
            "base_variant": self.base_variant,
            "specification": self.specification,
            "assistance": self.assistance,
            "test_doubles": self.test_doubles,
            "code_checksum": self.code_checksum,
            "weights_checksum": self.weights_checksum,
            _PROVENANCE_FIELD: self.provenance,
        }


@dataclass(frozen=True, slots=True)
class ExperimentPlan:
    """Truth-free immutable execution plan."""

    __module__ = "sird_experiment.models"

    experiment_id: str
    plan_version: str
    mode: ExperimentMode | str
    manifest_version: str
    sample_ids: tuple[str, ...]
    sample_checksums: Mapping[str, str]
    variants: tuple[ExperimentVariant, ...]
    seed: int = 0
    repeats: int = 1
    pair_order: tuple[tuple[str, str, int], ...] | None = None
    partitions: Mapping[str, str] = field(default_factory=dict)
    resources: Mapping[str, Any] = field(default_factory=dict)
    metrics: tuple[str, ...] = ()
    hard_boundaries: Mapping[str, Any] = field(default_factory=dict)
    failure_rules: Mapping[str, Any] = field(default_factory=dict)
    output_policy: Mapping[str, Any] = field(default_factory=dict)
    intermediate_material_mode: str = "none"
    provenance: Mapping[str, str] = field(default_factory=dict)
    plan_hash: str | None = None

    def __post_init__(self) -> None:
        mode, checksums = _prepare_plan(self)
        _freeze_identifiers(self, mode, checksums)
        _freeze_metadata(self)
        _finalize_pairs(self)

    @property
    def corpus_version(self) -> str:
        """Alias for callers that name the manifest version as corpus data."""
        return self.manifest_version

    def expand_pairs(self) -> tuple[tuple[str, str, int], ...]:
        """Return the immutable deterministic execution order."""
        return _expanded_pairs(self.pair_order)

    def working_manifest(self) -> Mapping[str, Any]:
        """Return the bounded manifest passed to execution, without truth."""
        return MappingProxyType(
            {
                "manifest_version": self.manifest_version,
                "corpus_version": self.manifest_version,
                "sample_ids": self.sample_ids,
                "sample_checksums": self.sample_checksums,
                "partitions": self.partitions,
                "provenance": self.provenance,
            }
        )

    def variant(self, variant_id: str) -> ExperimentVariant:
        for variant in self.variants:
            if variant.variant_id == variant_id:
                return variant
        raise KeyError(variant_id)

    def _generate_pairs(self) -> tuple[tuple[str, str, int], ...]:
        pairs: list[tuple[str, str, int]] = []
        for repeat in range(self.repeats):
            for sample_id in self.sample_ids:
                for variant in self.variants:
                    pairs.append((sample_id, variant.variant_id, repeat))
        random.Random(self.seed).shuffle(pairs)
        return tuple(pairs)

    def _hash_material(self) -> Mapping[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "plan_version": self.plan_version,
            "mode": self.mode,
            "manifest_version": self.manifest_version,
            "sample_ids": self.sample_ids,
            "sample_checksums": self.sample_checksums,
            "variants": tuple(
                variant.to_mapping() for variant in self.variants
            ),
            "seed": self.seed,
            "repeats": self.repeats,
            "pair_order": self.pair_order,
            "partitions": self.partitions,
            "resources": self.resources,
            "metrics": self.metrics,
            "hard_boundaries": self.hard_boundaries,
            "failure_rules": self.failure_rules,
            "output_policy": self.output_policy,
            "intermediate_material_mode": self.intermediate_material_mode,
            "provenance": self.provenance,
        }
