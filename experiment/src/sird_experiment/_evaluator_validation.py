"""Validation stages for saved prediction evaluation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sird_experiment.models import (
    ExperimentMode,
    ExperimentPlan,
    PredictionRecord,
)


def _pair_error(
    plan: ExperimentPlan, records: Sequence[PredictionRecord]
) -> str | None:
    expected_pairs = set(plan.expand_pairs())
    actual_pairs = {
        (record.sample_id, record.variant_id, record.repeat_id)
        for record in records
    }
    pairs_match = actual_pairs == expected_pairs
    counts_match = len(records) == len(expected_pairs)
    if not pairs_match or not counts_match:
        return "missing or duplicate prediction pairs"
    return None


def _record_error(
    plan: ExperimentPlan,
    records: Sequence[PredictionRecord],
    truth: Mapping[str, Any],
) -> tuple[str, str] | None:
    for record in records:
        if record.input_checksum != plan.sample_checksums.get(
            record.sample_id
        ):
            return "checksum", "prediction input checksum mismatch"
        variant = plan.variant(record.variant_id)
        substitution = (
            record.assistance != variant.assistance
            or record.test_doubles != variant.test_doubles
        )
        if substitution:
            return (
                "substitution",
                "undeclared substitution in prediction record",
            )
        end_to_end_substitution = plan.mode is ExperimentMode.END_TO_END and (
            record.assistance or record.test_doubles
        )
        if end_to_end_substitution:
            return (
                "substitution",
                "component substitution cannot be scored end_to_end",
            )
        if record.sample_id not in truth:
            return "truth", "missing protected truth pair"
    return None


def _truth_checksum_error(
    plan: ExperimentPlan,
    truth_checksums: Mapping[str, str] | None,
) -> str | None:
    if truth_checksums is None:
        return None
    for sample_id in plan.sample_ids:
        if sample_id not in truth_checksums:
            return "missing protected truth checksum"
        checksum = truth_checksums[sample_id]
        if not isinstance(checksum, str) or not checksum.strip():
            return "invalid protected truth checksum"
    return None


def _metric_error(metric: str) -> str | None:
    if metric != "exact_match":
        return f"unsupported metric: {metric}"
    return None
