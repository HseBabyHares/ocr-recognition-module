"""Request parsing models for the recognition runtime."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from sird_recognition.codes import TechnicalCode

_DOCUMENTED_REQUEST_KEYS = frozenset(
    ("task_id", "request_id", "artifact_capability", "limits", "policy_ref")
)


class RecognitionError(ValueError):
    """Typed technical failure raised by a recognition stage or ingress."""

    def __init__(
        self,
        code: TechnicalCode | str,
        *,
        retryable: bool = False,
        message: str | None = None,
    ) -> None:
        self.code = code
        self.technical_code = code
        self.retryable = retryable
        super().__init__(message or str(code))


@dataclass(frozen=True, slots=True)
class RecognizeRequest:
    """Strict, transport-neutral request accepted by the OCR runtime."""

    task_id: str
    request_id: str
    artifact_capability: str
    limits: Mapping[str, int]
    policy_ref: str

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> RecognizeRequest:
        """Parse only the documented ingress keys and reject selectors."""
        if not isinstance(payload, Mapping):
            raise RecognitionError(TechnicalCode.INVALID_INPUT)
        if set(payload) != _DOCUMENTED_REQUEST_KEYS:
            raise RecognitionError(TechnicalCode.INVALID_INPUT)
        parsed_strings = _parse_request_strings(payload)
        return cls(
            task_id=parsed_strings[0],
            request_id=parsed_strings[1],
            artifact_capability=parsed_strings[2],
            limits=_parse_request_limits(payload["limits"]),
            policy_ref=parsed_strings[3],
        )


def _parse_request_strings(
    payload_values: Mapping[str, object],
) -> tuple[str, str, str, str]:
    string_keys = (
        "task_id",
        "request_id",
        "artifact_capability",
        "policy_ref",
    )
    for string_key in string_keys:
        string_value = payload_values[string_key]
        if not isinstance(string_value, str) or not string_value:
            raise RecognitionError(TechnicalCode.INVALID_INPUT)
    return (
        cast(str, payload_values["task_id"]),
        cast(str, payload_values["request_id"]),
        cast(str, payload_values["artifact_capability"]),
        cast(str, payload_values["policy_ref"]),
    )


def _parse_request_limits(limit_payload: object) -> dict[str, int]:
    if not isinstance(limit_payload, Mapping):
        raise RecognitionError(TechnicalCode.INVALID_INPUT)
    parsed_limits: dict[str, int] = {}
    for limit_name, limit_amount in limit_payload.items():
        if not _valid_limit(limit_name, limit_amount):
            raise RecognitionError(TechnicalCode.INVALID_INPUT)
        parsed_limits[cast(str, limit_name)] = cast(int, limit_amount)
    return parsed_limits


def _valid_limit(limit_name: object, limit_amount: object) -> bool:
    if not isinstance(limit_name, str) or not limit_name:
        return False
    if isinstance(limit_amount, bool) or not isinstance(limit_amount, int):
        return False
    return limit_amount >= 0
