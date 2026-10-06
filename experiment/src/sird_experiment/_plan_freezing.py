"""Immutable field normalization for experiment plans."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from sird_experiment._model_enums import ExperimentMode
from sird_experiment._model_serialization import _freeze

if TYPE_CHECKING:
    from sird_experiment._model_plan import ExperimentPlan


def _freeze_identifiers(
    plan: ExperimentPlan,
    mode: ExperimentMode,
    checksums: Mapping[str, str],
) -> None:
    object.__setattr__(plan, "mode", mode)
    object.__setattr__(plan, "sample_ids", tuple(plan.sample_ids))
    object.__setattr__(plan, "sample_checksums", _freeze(dict(checksums)))
    object.__setattr__(plan, "variants", tuple(plan.variants))


def _freeze_metadata(plan: ExperimentPlan) -> None:
    object.__setattr__(plan, "partitions", _freeze(dict(plan.partitions)))
    object.__setattr__(plan, "resources", _freeze(dict(plan.resources)))
    object.__setattr__(plan, "metrics", tuple(plan.metrics))
    object.__setattr__(
        plan,
        "hard_boundaries",
        _freeze(dict(plan.hard_boundaries)),
    )
    object.__setattr__(
        plan,
        "failure_rules",
        _freeze(dict(plan.failure_rules)),
    )
    object.__setattr__(plan, "provenance", _freeze(dict(plan.provenance)))
