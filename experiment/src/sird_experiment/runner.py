"""Injected-callable experiment execution with no production OCR imports."""

from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from sird_experiment._runner_helpers import (
    _context_for,
    _ExecutionContext,
    _failed_record,
    _missing_executor_record,
    _record_from_result,
    _replay_record,
)
from sird_experiment.models import (
    ExperimentMode,
    ExperimentPlan,
    SampleExecutionRecord,
)


class ExperimentRunner:
    """Execute planned pairs through an injected callable.

    The callable receives only public sample identity, variant, and repeat. It
    never receives protected truth. A replay plan intentionally produces
    ``not_run`` records and never invokes the callable.
    """

    def __init__(self, executor: Callable[..., Any] | None = None) -> None:
        self._executor = executor

    def run(self, plan: ExperimentPlan) -> tuple[SampleExecutionRecord, ...]:
        records: list[SampleExecutionRecord] = []
        for pair in plan.expand_pairs():
            records.append(self._run_pair(plan, pair))
        return tuple(records)

    execute = run

    def _run_pair(
        self,
        plan: ExperimentPlan,
        pair: tuple[str, str, int],
    ) -> SampleExecutionRecord:
        sample_id, variant_id, repeat_id = pair
        context = _context_for(
            plan,
            sample_id,
            variant_id,
            repeat_id,
            plan.variant(variant_id),
        )
        if plan.mode is ExperimentMode.REPLAY_METRICS:
            return _replay_record(context)
        if self._executor is None:
            return _missing_executor_record(context)
        return self._execute_pair(context)

    def _execute_pair(
        self, context: _ExecutionContext
    ) -> SampleExecutionRecord:
        started = time.perf_counter()
        try:
            execution_result = self._invoke(
                context.sample_id,
                context.variant,
                context.repeat_id,
            )
        except Exception as execution_error:
            elapsed = (time.perf_counter() - started) * 1000
            return _failed_record(context, execution_error, elapsed)
        elapsed = (time.perf_counter() - started) * 1000
        completed = replace(context, wall_time_ms=elapsed)
        return _record_from_result(execution_result, completed)

    def _invoke(self, sample_id: str, variant: Any, repeat_id: int) -> Any:
        assert self._executor is not None
        try:
            signature = inspect.signature(self._executor)
        except (TypeError, ValueError):
            arguments = (sample_id, variant, repeat_id)
        else:
            positional = [
                parameter
                for parameter in signature.parameters.values()
                if parameter.kind
                in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
            ]
            has_varargs = any(
                parameter.kind is parameter.VAR_POSITIONAL
                for parameter in signature.parameters.values()
            )
            argument_count = 3 if has_varargs else min(len(positional), 3)
            arguments = (sample_id, variant, repeat_id)[:argument_count]
        return self._executor(*arguments)
