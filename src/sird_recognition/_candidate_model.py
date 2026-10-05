"""Private GLiNER label and prediction helpers."""

import inspect
from collections.abc import Callable, ValuesView
from typing import Any, cast

_LABEL_PROMPT_PAIRS: tuple[tuple[str, str], ...] = (
    ("person", "full_name"),
    ("date of birth", "birth_date"),
    ("place of birth", "birth_place"),
    ("registration date", "registration_date"),
)
_LABELS: tuple[str, ...] = tuple(prompt for prompt, _ in _LABEL_PROMPT_PAIRS)


def labels() -> tuple[str, ...]:
    """Return the stable labels sent to the candidate model."""
    return _LABELS


def field_name(label: str) -> str | None:
    """Map a model label to its candidate field name."""
    normalized_label = label.strip().casefold()
    for prompt, candidate_field in _LABEL_PROMPT_PAIRS:
        if normalized_label in {prompt, candidate_field}:
            return candidate_field
    return None


def _signature_parameters(
    predict: object,
) -> ValuesView[inspect.Parameter] | None:
    try:
        signature = inspect.signature(
            cast(Callable[..., Any], predict),
        )
    except (TypeError, ValueError):
        return None
    return signature.parameters.values()


def predict_capabilities(
    predict: object,
) -> tuple[bool, str | None, bool]:
    """Inspect optional threshold and CPU-thread prediction parameters."""
    signature_parameters = _signature_parameters(predict)
    if signature_parameters is None:
        return True, None, False
    accepts_threshold = any(
        parameter.name == "threshold"
        or parameter.kind is parameter.VAR_KEYWORD
        for parameter in signature_parameters
    )
    cpu_thread_parameter = next(
        (
            parameter.name
            for parameter in signature_parameters
            if parameter.name in {"cpu_threads", "num_threads"}
        ),
        None,
    )
    accepts_cpu_threads = cpu_thread_parameter is not None or any(
        parameter.kind is parameter.VAR_KEYWORD
        for parameter in signature_parameters
    )
    return accepts_threshold, cpu_thread_parameter, accepts_cpu_threads


def prediction_kwargs(
    capabilities: tuple[bool, str | None, bool],
    threshold: float,
    cpu_threads: int,
) -> dict[str, object]:
    """Build only prediction keywords accepted by a model implementation."""
    kwargs: dict[str, object] = {}
    if capabilities[0]:
        kwargs["threshold"] = threshold
    if capabilities[2]:
        kwargs[capabilities[1] or "cpu_threads"] = cpu_threads
    return kwargs
