"""Validation helpers for experiment plans."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sird_experiment._model_enums import ExperimentMode
from sird_experiment._model_safety import _check_safe, _text

if TYPE_CHECKING:
    from sird_experiment._model_plan import ExperimentPlan


def _validate_samples(plan: ExperimentPlan) -> None:
    _validate_sample_ids(plan.sample_ids)
    _validate_variants(plan.variants)
    if plan.repeats < 1:
        raise ValueError("repeats must be positive")


def _validate_sample_ids(sample_ids: tuple[str, ...]) -> None:
    if not sample_ids:
        raise ValueError("sample_ids must not be empty")
    if len(set(sample_ids)) != len(sample_ids) or any(
        not str(sample_id).strip() for sample_id in sample_ids
    ):
        raise ValueError("sample_ids must be unique and non-empty")


def _validate_variants(variants: tuple) -> None:
    if not variants:
        raise ValueError("variants must not be empty")
    variant_ids = tuple(variant.variant_id for variant in variants)
    if len(set(variant_ids)) != len(variant_ids):
        raise ValueError("variant_id values must be unique")


def _validate_checksums(
    sample_ids: tuple[str, ...], checksums: dict[str, str]
) -> None:
    if set(checksums) != set(sample_ids):
        raise ValueError(
            "sample_checksums must contain exactly every sample_id"
        )
    for sample_id, checksum in checksums.items():
        _text(checksum, f"sample_checksums[{sample_id}]")


def _safe_plan_metadata(plan: ExperimentPlan) -> None:
    metadata = (
        plan.partitions,
        plan.resources,
        plan.hard_boundaries,
        plan.failure_rules,
        plan.output_policy,
        plan.provenance,
    )
    for metadata_item in metadata:
        _check_safe(metadata_item)


def _prepare_plan(
    plan: ExperimentPlan,
) -> tuple[ExperimentMode, dict[str, str]]:
    _text(plan.experiment_id, "experiment_id")
    _text(plan.plan_version, "plan_version")
    _text(plan.manifest_version, "manifest_version")
    mode = ExperimentMode(plan.mode)
    _validate_samples(plan)
    checksums = dict(plan.sample_checksums)
    _validate_checksums(plan.sample_ids, checksums)
    _safe_plan_metadata(plan)
    return mode, checksums
