"""Record construction helpers for deterministic experiment execution."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from sird_experiment.models import (
    ExperimentMode,
    ExperimentPlan,
    ExperimentVariant,
    PredictionRecord,
    SampleExecutionRecord,
    SampleStatus,
)


@dataclass(frozen=True, slots=True)
class _ExecutionContext:
    run_id: str
    sample_id: str
    variant_id: str
    repeat_id: int
    variant: ExperimentVariant
    mode: ExperimentMode
    input_checksum: str
    resolved_spec_hash: str
    assistance: tuple[str, ...]
    test_doubles: tuple[str, ...]
    wall_time_ms: float


def _context_for(
    plan: ExperimentPlan,
    sample_id: str,
    variant_id: str,
    repeat_id: int,
    variant: ExperimentVariant,
) -> _ExecutionContext:
    return _ExecutionContext(
        run_id=f"{plan.experiment_id}:{sample_id}:{variant_id}:{repeat_id}",
        sample_id=sample_id,
        variant_id=variant_id,
        repeat_id=repeat_id,
        variant=variant,
        mode=cast(ExperimentMode, plan.mode),
        input_checksum=plan.sample_checksums[sample_id],
        resolved_spec_hash=variant.resolved_spec_hash,
        assistance=variant.assistance,
        test_doubles=variant.test_doubles,
        wall_time_ms=0,
    )


def _replay_record(context: _ExecutionContext) -> SampleExecutionRecord:
    return SampleExecutionRecord(
        run_id=context.run_id,
        sample_id=context.sample_id,
        variant_id=context.variant_id,
        repeat_id=context.repeat_id,
        mode=context.mode,
        status=SampleStatus.NOT_RUN,
        input_checksum=context.input_checksum,
        resolved_spec_hash=context.resolved_spec_hash,
        assistance=context.assistance,
        test_doubles=context.test_doubles,
        reason="replay_metrics does not execute OCR",
    )


def _missing_executor_record(
    context: _ExecutionContext,
) -> SampleExecutionRecord:
    return SampleExecutionRecord(
        run_id=context.run_id,
        sample_id=context.sample_id,
        variant_id=context.variant_id,
        repeat_id=context.repeat_id,
        mode=context.mode,
        status=SampleStatus.NOT_RUN,
        input_checksum=context.input_checksum,
        resolved_spec_hash=context.resolved_spec_hash,
        assistance=context.assistance,
        test_doubles=context.test_doubles,
        reason="no execution callable was provided",
    )


def _failed_record(
    context: _ExecutionContext,
    error: Exception,
    wall_time_ms: float,
) -> SampleExecutionRecord:
    return SampleExecutionRecord(
        run_id=context.run_id,
        sample_id=context.sample_id,
        variant_id=context.variant_id,
        repeat_id=context.repeat_id,
        mode=context.mode,
        status=SampleStatus.FAILED,
        input_checksum=context.input_checksum,
        resolved_spec_hash=context.resolved_spec_hash,
        assistance=context.assistance,
        test_doubles=context.test_doubles,
        reason=f"execution failed: {type(error).__name__}",
        wall_time_ms=wall_time_ms,
    )


def _record_from_mapping(
    mapping_values: Mapping[str, Any], context: _ExecutionContext
) -> SampleExecutionRecord:
    status = SampleStatus(mapping_values.get("status", SampleStatus.OK))
    return SampleExecutionRecord(
        run_id=context.run_id,
        sample_id=context.sample_id,
        variant_id=context.variant_id,
        repeat_id=context.repeat_id,
        mode=context.mode,
        status=status,
        input_checksum=context.input_checksum,
        resolved_spec_hash=context.resolved_spec_hash,
        assistance=tuple(mapping_values.get("assistance", context.assistance)),
        test_doubles=tuple(
            mapping_values.get("test_doubles", context.test_doubles)
        ),
        applied_execution=mapping_values.get("applied_execution", {}),
        module_result_ref=mapping_values.get("module_result_ref"),
        stage_records=tuple(mapping_values.get("stage_records", ())),
        reason=str(mapping_values.get("reason", status.value)),
        failed_stage=mapping_values.get("failed_stage"),
        wall_time_ms=mapping_values.get("wall_time_ms", context.wall_time_ms),
        cpu_time_ms=mapping_values.get("cpu_time_ms"),
        peak_rss_bytes=mapping_values.get("peak_rss_bytes"),
        gpu_peak_bytes=mapping_values.get("gpu_peak_bytes"),
        cache_hits=int(mapping_values.get("cache_hits", 0)),
        warmup_state=mapping_values.get("warmup_state"),
        provenance=mapping_values.get("provenance", {}),
    )


def _record_from_result(
    execution_result: Any, context: _ExecutionContext
) -> SampleExecutionRecord:
    if isinstance(execution_result, SampleExecutionRecord):
        if (
            execution_result.sample_id,
            execution_result.variant_id,
            execution_result.repeat_id,
        ) != (context.sample_id, context.variant_id, context.repeat_id):
            raise ValueError(
                "executor returned a record for a different planned pair"
            )
        return execution_result
    if isinstance(execution_result, PredictionRecord):
        return SampleExecutionRecord(
            run_id=context.run_id,
            sample_id=context.sample_id,
            variant_id=context.variant_id,
            repeat_id=context.repeat_id,
            mode=context.mode,
            status=SampleStatus.OK,
            input_checksum=context.input_checksum,
            resolved_spec_hash=context.resolved_spec_hash,
            assistance=context.assistance,
            test_doubles=context.test_doubles,
            module_result_ref=execution_result.prediction_checksum,
            wall_time_ms=context.wall_time_ms,
        )
    mapping_values = (
        execution_result if isinstance(execution_result, Mapping) else {}
    )
    return _record_from_mapping(mapping_values, context)
