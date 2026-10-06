from __future__ import annotations

from collections.abc import MutableMapping
from functools import partial
from importlib import import_module
from typing import cast

import pytest

import sird_experiment as experiment
from sird_experiment import (
    EvaluationRecord,
    ExperimentMode,
    ExperimentPlan,
    ExperimentRunner,
    ExperimentStatus,
    ExperimentVariant,
    IndependentEvaluator,
    PredictionRecord,
)

_support = import_module("_test_support")

_EVALUATOR = IndependentEvaluator()


_SAMPLE_ONE = "s1"
_SAMPLE_TWO = "s2"
_CHECKSUM_ONE = "sha-s1"
_CHECKSUM_TWO = "sha-s2"
_SCHEMA_VERSION = "1"
_ASSISTED_VARIANT = "assisted"
_PLAIN_VARIANT = "plain"
_ASSISTANCE = "known_crop"


def test_plan_hash_and_immutability() -> None:
    plan = _support.plan()
    same = _support.plan()
    assert plan.plan_hash == same.plan_hash
    with pytest.raises(TypeError):
        checksums = cast(MutableMapping[str, str], plan.sample_checksums)
        checksums[_SAMPLE_ONE] = "changed"
    with pytest.raises(ValueError):
        ExperimentPlan(
            experiment_id=plan.experiment_id,
            plan_version=plan.plan_version,
            mode=plan.mode,
            manifest_version=plan.manifest_version,
            sample_ids=plan.sample_ids,
            sample_checksums=plan.sample_checksums,
            variants=plan.variants,
            seed=plan.seed,
            repeats=plan.repeats,
            plan_hash="wrong",
        )


def test_pair_order_is_seeded() -> None:
    first = _support.plan()
    second = _support.plan()
    changed = ExperimentPlan(
        experiment_id="exp-1",
        plan_version=_SCHEMA_VERSION,
        mode=ExperimentMode.REPLAY_METRICS,
        manifest_version="manifest-1",
        sample_ids=(_SAMPLE_ONE, _SAMPLE_TWO),
        sample_checksums={
            _SAMPLE_ONE: _CHECKSUM_ONE,
            _SAMPLE_TWO: _CHECKSUM_TWO,
        },
        variants=(ExperimentVariant("base"), ExperimentVariant("candidate")),
        seed=8,
        repeats=2,
    )
    assert first.pair_order == second.pair_order
    assert first.pair_order != changed.pair_order
    assert len(first.expand_pairs()) == 8


def test_runner_records_terminal_status() -> None:
    plan = _support.plan(ExperimentMode.END_TO_END)
    calls: list[tuple[str, str, int]] = []

    records = ExperimentRunner(partial(_support.record_execution, calls)).run(
        plan
    )
    assert len(records) == len(plan.expand_pairs())
    assert {record.status for record in records} == {
        experiment.SampleStatus.OK
    }
    assert len(calls) == len(plan.expand_pairs())


def test_replay_skips_ocr() -> None:
    plan = _support.one_variant_plan()
    called = [False]
    records = ExperimentRunner(partial(_support.mark_called, called)).run(plan)
    assert not called[0]
    assert {record.status for record in records} == {
        experiment.SampleStatus.NOT_RUN
    }
    evaluation = _EVALUATOR.evaluate(
        plan,
        _support.predictions(plan),
        {_SAMPLE_ONE: _SAMPLE_ONE, _SAMPLE_TWO: _SAMPLE_TWO},
    )
    assert evaluation.status is ExperimentStatus.PASS
    assert getattr(evaluation, "value", None) == 1


def test_missing_pair_blocks() -> None:
    plan = _support.one_variant_plan()
    missing = _EVALUATOR.evaluate(
        plan,
        _support.predictions(plan)[:-1],
        {_SAMPLE_ONE: _SAMPLE_ONE, _SAMPLE_TWO: _SAMPLE_TWO},
    )
    assert missing.status is ExperimentStatus.BLOCKED
    assert "pairs" in missing.reason
    bad = list(_support.predictions(plan))
    bad_record = bad[0]
    bad[0] = PredictionRecord(
        sample_id=bad_record.sample_id,
        variant_id=bad_record.variant_id,
        repeat_id=bad_record.repeat_id,
        schema_version=_SCHEMA_VERSION,
        payload=bad_record.payload,
        input_checksum="wrong",
    )
    checksum = _EVALUATOR.evaluate(
        plan,
        bad,
        {_SAMPLE_ONE: _SAMPLE_ONE, _SAMPLE_TWO: _SAMPLE_TWO},
    )
    assert checksum.status is ExperimentStatus.BLOCKED
    assert "checksum" in checksum.reason


def _evaluation(
    variant_id: str,
    assistance: tuple[str, ...] = (),
) -> EvaluationRecord:
    plan = _support.one_variant_plan(
        ExperimentMode.END_TO_END,
        ExperimentVariant(variant_id, assistance=assistance),
        repeats=1,
        sample_ids=(_SAMPLE_ONE,),
    )
    prediction = PredictionRecord(
        sample_id=_SAMPLE_ONE,
        variant_id=variant_id,
        repeat_id=0,
        schema_version=_SCHEMA_VERSION,
        payload={"value": _SAMPLE_ONE},
        input_checksum=_CHECKSUM_ONE,
        assistance=assistance,
    )
    return _EVALUATOR.evaluate(
        plan,
        (prediction,),
        {_SAMPLE_ONE: _SAMPLE_ONE},
    )


def test_end_to_end_assistance() -> None:
    blocked = _evaluation(_ASSISTED_VARIANT, (_ASSISTANCE,))
    passed = _evaluation(_PLAIN_VARIANT)
    assert blocked.status is ExperimentStatus.BLOCKED
    decision = IndependentEvaluator.select(
        {_ASSISTED_VARIANT: blocked, _PLAIN_VARIANT: passed},
        hard_boundaries={"min_value": 0.5},
    )
    assert decision.selected_variant_id == _PLAIN_VARIANT
    assert _ASSISTED_VARIANT in decision.exclusions
