"""Shared fixtures for experiment contract tests."""

from __future__ import annotations

from sird_experiment import (
    ExperimentMode,
    ExperimentPlan,
    ExperimentVariant,
    PredictionRecord,
)

_BASE_VARIANT_ID = "base"
_SCHEMA_VERSION = "1"


def record_execution(
    calls: list[tuple[str, str, int]],
    sample_id: str,
    variant: ExperimentVariant,
    repeat_id: int,
) -> dict[str, str]:
    calls.append((sample_id, variant.variant_id, repeat_id))
    return {"status": "ok", "module_result_ref": "ref"}


def mark_called(state: list[bool], *_: object) -> None:
    state[0] = True


def plan(
    mode: ExperimentMode = ExperimentMode.REPLAY_METRICS,
) -> ExperimentPlan:
    return ExperimentPlan(
        experiment_id="exp-1",
        plan_version=_SCHEMA_VERSION,
        mode=mode,
        manifest_version="manifest-1",
        sample_ids=("s1", "s2"),
        sample_checksums={"s1": "sha-s1", "s2": "sha-s2"},
        variants=(
            ExperimentVariant(_BASE_VARIANT_ID),
            ExperimentVariant("candidate"),
        ),
        seed=7,
        repeats=2,
    )


def predictions(
    experiment_plan: ExperimentPlan,
    variant_id: str = _BASE_VARIANT_ID,
) -> tuple[PredictionRecord, ...]:
    return tuple(
        PredictionRecord(
            sample_id=sample_id,
            variant_id=variant_id,
            repeat_id=repeat_id,
            schema_version=_SCHEMA_VERSION,
            payload={"value": sample_id},
            input_checksum=experiment_plan.sample_checksums[sample_id],
        )
        for sample_id, current_variant, repeat_id in (
            experiment_plan.expand_pairs()
        )
        if current_variant == variant_id
    )


def one_variant_plan(
    mode: ExperimentMode = ExperimentMode.REPLAY_METRICS,
    variant: ExperimentVariant | None = None,
    repeats: int = 2,
    sample_ids: tuple[str, ...] | None = None,
) -> ExperimentPlan:
    base = plan(mode)
    selected_samples = sample_ids or base.sample_ids
    return ExperimentPlan(
        experiment_id=base.experiment_id,
        plan_version=base.plan_version,
        mode=mode,
        manifest_version=base.manifest_version,
        sample_ids=selected_samples,
        sample_checksums={
            sample_id: base.sample_checksums[sample_id]
            for sample_id in selected_samples
        },
        variants=(variant or ExperimentVariant(_BASE_VARIANT_ID),),
        seed=base.seed,
        repeats=repeats,
    )
