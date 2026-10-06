"""Deterministic hard-boundary selection helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from sird_experiment.models import (
    EvaluationRecord,
    ExperimentMode,
    ExperimentStatus,
    SelectionDecision,
)


class _SelectionContext(NamedTuple):
    by_variant: dict[str, EvaluationRecord]
    boundaries: dict[str, Any]
    eligible: list[EvaluationRecord]
    exclusions: dict[str, tuple[str, ...]]
    rule: str
    winner: EvaluationRecord | None


def _reasons(
    record: EvaluationRecord,
    boundaries: Mapping[str, Any],
    mode: ExperimentMode | str,
) -> tuple[str, ...]:
    reasons: list[str] = []
    metric_value = getattr(record, "value", None)
    if ExperimentStatus(record.status) is not ExperimentStatus.PASS:
        reasons.append(
            f"evaluation status is {ExperimentStatus(record.status).value}"
        )
    if ExperimentMode(mode) is ExperimentMode.END_TO_END and record.exclusions:
        reasons.extend(record.exclusions)
    maximum = boundaries.get("max_value")
    if maximum is not None and (
        metric_value is None or metric_value > maximum
    ):
        reasons.append(f"value exceeds max_value={maximum}")
    minimum = boundaries.get("min_value")
    if minimum is not None and (
        metric_value is None or metric_value < minimum
    ):
        reasons.append(f"value below min_value={minimum}")
    metric_limit = boundaries.get(record.metric)
    if metric_limit is not None and (
        metric_value is None or metric_value < metric_limit
    ):
        reasons.append(f"metric below {record.metric}={metric_limit}")
    return tuple(reasons)


def _partition(
    by_variant: Mapping[str, EvaluationRecord],
    boundaries: Mapping[str, Any],
    mode: ExperimentMode | str,
) -> tuple[list[EvaluationRecord], dict]:
    exclusions: dict[str, tuple[str, ...]] = {}
    eligible: list[EvaluationRecord] = []
    for variant_id, record in by_variant.items():
        reasons = _reasons(record, boundaries, mode)
        if reasons:
            exclusions[variant_id] = reasons
        else:
            eligible.append(record)
    return eligible, exclusions


def _winner(
    eligible: Sequence[EvaluationRecord], rule: str
) -> EvaluationRecord | None:
    selectors = {
        "max_value": (
            lambda record: getattr(record, "value", None) or float("-inf"),
            True,
        ),
        "min_value": (
            lambda record: getattr(record, "value", None) or float("inf"),
            False,
        ),
    }
    selector, reverse = selectors.get(rule, (None, False))
    if selector is None:
        raise ValueError("unsupported selection rule")
    ordered = sorted(eligible, key=selector, reverse=reverse)
    return ordered[0] if ordered else None


def _selection_context(
    evaluations: Mapping[str, EvaluationRecord] | Sequence[EvaluationRecord],
    boundaries: Mapping[str, Any],
    rule: str,
    mode: ExperimentMode | str,
) -> _SelectionContext:
    if isinstance(evaluations, Mapping):
        by_variant = dict(evaluations)
    else:
        by_variant = {record.variant_id: record for record in evaluations}
    eligible, exclusions = _partition(by_variant, boundaries, mode)
    winner = _winner(eligible, rule)
    return _SelectionContext(
        by_variant=by_variant,
        boundaries=dict(boundaries),
        eligible=eligible,
        exclusions=exclusions,
        rule=rule,
        winner=winner,
    )


def _build_decision(context: _SelectionContext) -> SelectionDecision:
    winner = context.winner
    if winner is None:
        selected_variant = None
        status = ExperimentStatus.BLOCKED
        reason = "no eligible variant"
    else:
        selected_variant = winner.variant_id
        status = ExperimentStatus.PASS
        reason = "selected highest eligible metric"
    non_dominated = tuple(
        sorted(record.variant_id for record in context.eligible)
    )
    return SelectionDecision(
        status=status,
        selected_variant_id=selected_variant,
        considered_variants=tuple(sorted(context.by_variant)),
        exclusions=context.exclusions,
        non_dominated_variants=non_dominated,
        hard_boundaries=context.boundaries,
        rule=context.rule,
        reason=reason,
    )


def select_evaluations(
    evaluations: Mapping[str, EvaluationRecord] | Sequence[EvaluationRecord],
    hard_boundaries: Mapping[str, Any] | None,
    rule: str,
    mode: ExperimentMode | str,
) -> SelectionDecision:
    context = _selection_context(
        evaluations,
        hard_boundaries or {},
        rule,
        mode,
    )
    return _build_decision(context)
