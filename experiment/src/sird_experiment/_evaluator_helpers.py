"""Pure helpers for saved-prediction evaluation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from sird_experiment._evaluator_parsing import first_present
from sird_experiment.models import ExperimentPlan, PredictionRecord

_PREDICTION_KEYS = ("prediction", "value", "text", "result")
_TRUTH_KEYS = ("value", "text", "label", "reference")


def _prediction_value(payload: Mapping[str, Any]) -> Any:
    return first_present(payload, _PREDICTION_KEYS)


def _truth_value(candidate: Any) -> Any:
    if isinstance(candidate, Mapping):
        return first_present(candidate, _TRUTH_KEYS)
    return candidate


def _normalize(candidate: Any, policy: str) -> Any:
    if policy == "identity":
        return candidate
    if policy == "strip_casefold" and isinstance(candidate, str):
        return candidate.strip().casefold()
    raise ValueError(f"unsupported normalization policy: {policy}")


def _hash_predictions(records: Sequence[PredictionRecord]) -> str:
    checksums = (record.prediction_checksum or "" for record in records)
    serialized = "|".join(sorted(checksums))
    return hashlib.sha256(serialized.encode()).hexdigest()


def _hash_truth(truth: Mapping[str, Any], sample_ids: Sequence[str]) -> str:
    truth_pairs = [(sample_id, truth[sample_id]) for sample_id in sample_ids]
    serialized = json.dumps(
        truth_pairs,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


def _single_variant(records: Sequence[PredictionRecord]) -> str:
    variants = {record.variant_id for record in records}
    return next(iter(variants)) if len(variants) == 1 else "multiple"


def _plan_for_variant(plan: ExperimentPlan, variant_id: str) -> ExperimentPlan:
    pairs = tuple(
        pair for pair in plan.expand_pairs() if pair[1] == variant_id
    )
    return ExperimentPlan(
        experiment_id=plan.experiment_id,
        plan_version=plan.plan_version,
        mode=plan.mode,
        manifest_version=plan.manifest_version,
        sample_ids=plan.sample_ids,
        sample_checksums=plan.sample_checksums,
        variants=(plan.variant(variant_id),),
        seed=plan.seed,
        repeats=plan.repeats,
        pair_order=pairs,
        partitions=plan.partitions,
        resources=plan.resources,
        metrics=plan.metrics,
        hard_boundaries=plan.hard_boundaries,
        failure_rules=plan.failure_rules,
        output_policy=plan.output_policy,
        intermediate_material_mode=plan.intermediate_material_mode,
    )
