"""Private model inference flow for candidate extraction."""

from __future__ import annotations

import time
from collections import abc
from dataclasses import dataclass

from sird_recognition._candidate_resources import (
    ResourceContext,
    check_resources,
    collect_spans,
)
from sird_recognition._candidate_tracing import TracingPeak
from sird_recognition.candidate_contracts import (
    CandidateSpan,
    CandidateStageLimitError,
    CandidateStageUnavailableError,
)
from sird_recognition.contracts.text_observation import TextObservation

_FAILED_EVENT = "failed"
_UNAVAILABLE_STATE = "unavailable"
_WITHIN_LIMIT_STATE = "within_limit"


@dataclass(slots=True)
class InferenceContext:
    """Dependencies used by one model inference."""

    resources: ResourceContext
    emit: abc.Callable[[str, float, int, str, str], None]
    predict: abc.Callable[[object, str], object]
    started: float


def _emit_unavailable(context: InferenceContext) -> None:
    context.emit(
        _FAILED_EVENT,
        time.monotonic() - context.started,
        0,
        "inference_unavailable",
        _UNAVAILABLE_STATE,
    )


def _predict_with_diagnostics(
    context: InferenceContext,
    model: object,
    text: str,
) -> object:
    try:
        return context.predict(model, text)
    except CandidateStageUnavailableError:
        _emit_unavailable(context)
        raise
    except Exception as error:
        _emit_unavailable(context)
        raise CandidateStageUnavailableError(
            "candidate model inference is unavailable",
        ) from error


def _finish_inference(
    context: InferenceContext,
    model_output: object,
    text: str,
    observation: TextObservation,
) -> tuple[CandidateSpan, ...]:
    elapsed = check_resources(context.resources, context.started)
    if isinstance(model_output, (str, bytes, abc.Mapping)) or not isinstance(
        model_output,
        abc.Iterable,
    ):
        context.emit(
            _FAILED_EVENT,
            elapsed,
            0,
            "invalid_model_output",
            _UNAVAILABLE_STATE,
        )
        raise CandidateStageUnavailableError(
            "candidate model returned an invalid result",
        )
    spans = collect_spans(
        context.resources,
        model_output,
        text,
        observation,
        elapsed,
    )
    elapsed = time.monotonic() - context.started
    context.emit(
        "completed",
        elapsed,
        len(spans),
        "ok",
        _WITHIN_LIMIT_STATE,
    )
    return tuple(spans)


def run_inference(
    context: InferenceContext,
    model: object,
    text: str,
    observation: TextObservation,
) -> tuple[CandidateSpan, ...]:
    """Run one bounded model call and translate its output."""
    with TracingPeak():
        model_output = _predict_with_diagnostics(context, model, text)
        try:
            return _finish_inference(
                context,
                model_output,
                text,
                observation,
            )
        except CandidateStageLimitError:
            raise
        except CandidateStageUnavailableError:
            _emit_unavailable(context)
            raise
        except Exception as error:
            _emit_unavailable(context)
            raise CandidateStageUnavailableError(
                "candidate model inference is unavailable",
            ) from error
