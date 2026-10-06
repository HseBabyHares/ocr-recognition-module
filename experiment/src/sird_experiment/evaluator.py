"""Truth-isolated metric replay and saved prediction ingestion."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, NamedTuple, TypedDict, Unpack, cast

from sird_experiment._evaluator_helpers import (
    _hash_predictions,
    _hash_truth,
    _normalize,
    _plan_for_variant,
    _prediction_value,
    _single_variant,
    _truth_value,
)
from sird_experiment._evaluator_parsing import coerce_record
from sird_experiment._evaluator_validation import (
    _metric_error,
    _pair_error,
    _record_error,
    _truth_checksum_error,
)
from sird_experiment._selection import select_evaluations
from sird_experiment.models import (
    EvaluationRecord,
    ExperimentMode,
    ExperimentPlan,
    ExperimentStatus,
    PredictionRecord,
    SelectionDecision,
)


class _EvaluateOptions(TypedDict, total=False):
    metric: str
    normalization_policy: str
    truth_checksums: Mapping[str, str] | None


class _EvaluationOptions(NamedTuple):
    metric: str
    normalization_policy: str
    truth_checksums: Mapping[str, str] | None


def _evaluation_options(kwargs: _EvaluateOptions) -> _EvaluationOptions:
    allowed = {"metric", "normalization_policy", "truth_checksums"}
    unexpected = set(kwargs) - allowed
    if unexpected:
        unexpected_name = next(iter(unexpected))
        raise TypeError(
            "evaluate() got an unexpected keyword argument "
            f"{unexpected_name!r}"
        )
    return _EvaluationOptions(
        metric=kwargs.get("metric", "exact_match"),
        normalization_policy=kwargs.get("normalization_policy", "identity"),
        truth_checksums=kwargs.get("truth_checksums"),
    )


def ingest_predictions(
    saved: Iterable[PredictionRecord | Mapping[str, Any]],
    *,
    schema_version: str = "1",
) -> tuple[PredictionRecord, ...]:
    """Load bounded saved predictions and reject malformed schema records."""
    records = []
    for saved_record in saved:
        record = coerce_record(saved_record, schema_version)
        if record.schema_version != schema_version:
            raise ValueError("incompatible prediction schema")
        records.append(record)
    return tuple(records)


def _matching_count(
    records: Sequence[PredictionRecord],
    truth: Mapping[str, Any],
    normalization_policy: str,
) -> int:
    matches = 0
    for prediction_record in records:
        observed = _prediction_value(prediction_record.payload)
        expected = _truth_value(truth[prediction_record.sample_id])
        if _normalize(observed, normalization_policy) == _normalize(
            expected, normalization_policy
        ):
            matches += 1
    return matches


def _build_evaluation(
    records: Sequence[PredictionRecord],
    plan: ExperimentPlan,
    truth: Mapping[str, Any],
    options: _EvaluationOptions,
    evaluator_version: str,
) -> EvaluationRecord:
    matches = _matching_count(records, truth, options.normalization_policy)
    prediction_hash = _hash_predictions(records)
    truth_hash = _hash_truth(truth, plan.sample_ids)
    score = matches / len(records) if records else None
    return cast(Any, EvaluationRecord)(
        variant_id=_single_variant(records),
        metric=options.metric,
        status=ExperimentStatus.PASS,
        evaluator_version=evaluator_version,
        normalization_policy=options.normalization_policy,
        numerator=matches,
        denominator=len(records),
        value=score,
        prediction_hash=prediction_hash,
        truth_hash=truth_hash,
        reason="metric evaluated from saved predictions",
    )


class IndependentEvaluator:
    """Evaluate saved predictions against separately supplied protected
    truth."""

    def __init__(
        self, evaluator_version: str = "1", schema_version: str = "1"
    ) -> None:
        self.evaluator_version = evaluator_version
        self.schema_version = schema_version

    def evaluate(
        self,
        plan: ExperimentPlan,
        predictions: Iterable[PredictionRecord | Mapping[str, Any]],
        truth: Mapping[str, Any],
        **kwargs: Unpack[_EvaluateOptions],
    ) -> EvaluationRecord:
        """Return one bounded aggregate record, or blocked evidence.

        Truth is consumed for comparison and hashes only. It is never copied to
        the returned record or to any working prediction structure.
        """
        options = _evaluation_options(kwargs)
        try:
            records = ingest_predictions(
                predictions, schema_version=self.schema_version
            )
        except (TypeError, ValueError) as schema_error:
            return self._blocked("schema", str(schema_error), options.metric)
        blocked = self._validate_records(plan, records, truth, options)
        if blocked is not None:
            return blocked
        return _build_evaluation(
            records,
            plan,
            truth,
            options,
            self.evaluator_version,
        )

    def evaluate_many(
        self,
        plan: ExperimentPlan,
        predictions: Iterable[PredictionRecord | Mapping[str, Any]],
        truth: Mapping[str, Any],
        **kwargs: Unpack[_EvaluateOptions],
    ) -> tuple[EvaluationRecord, ...]:
        """Evaluate one record per variant while preserving shared
        validation."""
        records = ingest_predictions(
            predictions, schema_version=self.schema_version
        )
        output: list[EvaluationRecord] = []
        for variant in plan.variants:
            subset = tuple(
                prediction_record
                for prediction_record in records
                if prediction_record.variant_id == variant.variant_id
            )
            variant_plan = _plan_for_variant(plan, variant.variant_id)
            output.append(self.evaluate(variant_plan, subset, truth, **kwargs))
        return tuple(output)

    @classmethod
    def select(
        cls,
        evaluations: Mapping[str, EvaluationRecord]
        | Sequence[EvaluationRecord],
        *,
        hard_boundaries: Mapping[str, Any] | None = None,
        rule: str = "max_value",
        mode: ExperimentMode | str = ExperimentMode.END_TO_END,
    ) -> SelectionDecision:
        """Build selection evidence and exclude every hard-boundary
        violation."""
        return select_evaluations(evaluations, hard_boundaries, rule, mode)

    def _validate_records(
        self,
        plan: ExperimentPlan,
        records: Sequence[PredictionRecord],
        truth: Mapping[str, Any],
        options: _EvaluationOptions,
    ) -> EvaluationRecord | None:
        pair_error = _pair_error(plan, records)
        if pair_error is not None:
            return self._blocked("pairs", pair_error, options.metric)
        record_error = _record_error(plan, records, truth)
        if record_error is not None:
            return self._blocked(
                record_error[0], record_error[1], options.metric
            )
        checksum_error = _truth_checksum_error(plan, options.truth_checksums)
        if checksum_error is not None:
            return self._blocked(
                "truth_checksum", checksum_error, options.metric
            )
        metric_error = _metric_error(options.metric)
        if metric_error is not None:
            return self._blocked("metric", metric_error, options.metric)
        return None

    def _blocked(
        self, kind: str, reason: str, metric: str
    ) -> EvaluationRecord:
        return EvaluationRecord(
            variant_id="blocked",
            metric=metric,
            status=ExperimentStatus.BLOCKED,
            evaluator_version=self.evaluator_version,
            reason=f"{kind}: {reason}",
            exclusions=(reason,),
        )
