"""Private resource checks and span collection for candidate inference."""

import time
import tracemalloc
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from sird_recognition._candidate_translation import (
    TranslationSource,
    translate_candidate,
)
from sird_recognition.candidate_contracts import (
    CandidateSpan,
    CandidateStageLimitError,
)
from sird_recognition.contracts.text_observation import TextObservation

_LIMITED_EVENT = "limited"
_LIMITED_STATE = "limited"


@dataclass(slots=True)
class ResourceContext:
    """Resource and provenance dependencies used during one extraction."""

    timeout_seconds: float
    memory_limit_bytes: int
    max_candidates: int
    emit: Callable[[str, float, int, str, str], None]
    source: TranslationSource


def check_resources(context: ResourceContext, started: float) -> float:
    """Enforce elapsed-time and traced-memory limits."""
    elapsed = time.monotonic() - started
    _, peak = tracemalloc.get_traced_memory()
    if elapsed > context.timeout_seconds:
        context.emit(
            _LIMITED_EVENT,
            elapsed,
            0,
            "inference_timeout",
            _LIMITED_STATE,
        )
        raise CandidateStageLimitError("candidate inference timed out")
    if peak > context.memory_limit_bytes:
        context.emit(
            _LIMITED_EVENT,
            elapsed,
            0,
            "memory_limit",
            _LIMITED_STATE,
        )
        raise CandidateStageLimitError("candidate memory limit exceeded")
    return elapsed


def _append_span(
    context: ResourceContext,
    spans: list[CandidateSpan],
    span: CandidateSpan,
    elapsed: float,
) -> None:
    spans.append(span)
    if len(spans) > context.max_candidates:
        context.emit(
            _LIMITED_EVENT,
            elapsed,
            len(spans),
            "candidate_count_limit",
            _LIMITED_STATE,
        )
        raise CandidateStageLimitError(
            "candidate count limit exceeded",
        )


def collect_spans(
    context: ResourceContext,
    model_output: Iterable[object],
    text: str,
    observation: TextObservation,
    elapsed: float,
) -> list[CandidateSpan]:
    """Translate model records and enforce the candidate-count limit."""
    observation_id = getattr(observation, "observation_id", None)
    if not isinstance(observation_id, str) or not observation_id:
        observation_id = observation.adapter_id
    spans: list[CandidateSpan] = []
    for candidate_record in model_output:
        span = translate_candidate(
            candidate_record,
            text,
            observation,
            observation_id,
            context.source,
        )
        if span is not None:
            _append_span(context, spans, span, elapsed)
    return spans
