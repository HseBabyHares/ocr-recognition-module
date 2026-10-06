"""Pair-order validation and plan hash finalization."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sird_experiment._model_serialization import _digest

if TYPE_CHECKING:
    from sird_experiment._model_plan import ExperimentPlan


def finalize_pairs(plan: ExperimentPlan) -> None:
    """Validate supplied pairs and freeze the resulting plan hash."""
    generated = plan._generate_pairs()
    if plan.pair_order is not None:
        supplied = coerce_pair_order(plan.pair_order)
        ensure_same_pairs(supplied, generated)
        generated = supplied
    object.__setattr__(plan, "pair_order", generated)
    computed = _digest(plan._hash_material())
    validate_plan_hash(plan.plan_hash, computed)
    object.__setattr__(plan, "plan_hash", computed)


def coerce_pair_order(pair_order: tuple) -> tuple:
    return tuple(
        (str(sample), str(variant), int(repeat))
        for sample, variant, repeat in pair_order
    )


def ensure_same_pairs(supplied: tuple, generated: tuple) -> None:
    if not _same_pair_collection(supplied, generated):
        raise ValueError(
            "pair_order must contain each planned pair exactly once"
        )


def _same_pair_collection(first: tuple, second: tuple) -> bool:
    """Return whether pair collections have equal members and cardinality."""
    return _same_pair_members(first, second) and len(first) == len(second)


def _same_pair_members(first: tuple, second: tuple) -> bool:
    return set(first) == set(second)


def validate_plan_hash(plan_hash: str | None, computed: str) -> None:
    if plan_hash is not None and plan_hash != computed:
        raise ValueError("plan_hash does not match immutable plan content")
