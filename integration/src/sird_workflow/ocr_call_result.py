"""Result returned by the unary OCR client."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sird_workflow.ocr_outcome import OcrOutcome


@dataclass(frozen=True, slots=True, init=False)
class OcrCallResult:
    """Result returned by the unary OCR client."""

    outcome: OcrOutcome
    payload: Mapping[str, Any] | None
    error: str | None
    requeue: bool

    def __init__(
        self,
        outcome: OcrOutcome,
        *positional: object,
        **options: object,
    ) -> None:
        names = ("result", "error", "requeue")
        arguments = dict(zip(names, positional, strict=False))
        arguments.update(options)
        object.__setattr__(self, "outcome", OcrOutcome(outcome))
        payload = arguments.pop("result", None)
        if payload is None:
            payload = arguments.pop("payload", None)
        object.__setattr__(self, "payload", payload)
        object.__setattr__(self, "error", arguments.pop("error", None))
        object.__setattr__(self, "requeue", arguments.pop("requeue", False))
        if arguments:
            raise TypeError(
                f"unexpected keyword argument: {next(iter(arguments))}"
            )
        self.__post_init__()

    def __post_init__(self) -> None:
        if self.payload is not None and not isinstance(self.payload, Mapping):
            raise TypeError("OCR result must be a mapping")
        if not isinstance(self.requeue, bool):
            raise TypeError("OCR requeue flag must be boolean")


def _result_property(instance: OcrCallResult) -> Mapping[str, Any] | None:
    return instance.payload


type.__setattr__(OcrCallResult, "result", property(_result_property))
