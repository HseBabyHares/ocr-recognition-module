"""Field outcome records exchanged by OCR stages."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Unpack

from sird_recognition._field_result_arguments import (
    _FieldResultKeywords,
    field_result_arguments,
)


class FieldStatus(StrEnum):
    """Explicit outcome for one requested field."""

    __module__ = "sird_recognition.contracts.stages"

    EXTRACTED = "extracted"
    ABSENT = "absent"
    UNREADABLE = "unreadable"
    CONFLICT = "conflict"
    NOT_APPLICABLE = "not_applicable"
    NOT_PROCESSED = "not_processed"


@dataclass(frozen=True, slots=True, init=False)
class FieldResult:
    """Observed value and explicit status for one requested field."""

    status: FieldStatus
    field_value: object | None
    validations: tuple[object, ...]
    evidence_refs: tuple[str, ...]
    diagnostics: tuple[str, ...]
    required: bool

    def __init__(
        self,
        status: FieldStatus,
        *positional: object,
        **legacy_kwargs: Unpack[_FieldResultKeywords],
    ) -> None:
        field_value, metadata = field_result_arguments(
            positional,
            legacy_kwargs,
        )
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "field_value", field_value)
        object.__setattr__(self, "validations", metadata[0])
        object.__setattr__(self, "evidence_refs", metadata[1])
        object.__setattr__(self, "diagnostics", metadata[2])
        object.__setattr__(self, "required", metadata[3])
        self.__post_init__()

    def __post_init__(self) -> None:
        """Keep status, applicability, and value semantics explicit."""
        error_message = self._validation_error()
        if error_message is not None:
            raise ValueError(error_message)

    def _validation_error(self) -> str | None:
        if not isinstance(self.status, FieldStatus):
            return f"unknown field status: {self.status!r}"
        if not isinstance(self.required, bool):
            return "field applicability must be boolean"
        if self.status is FieldStatus.EXTRACTED and self.field_value is None:
            return "extracted field results require a value"
        if (
            self.status is not FieldStatus.EXTRACTED
            and self.field_value is not None
        ):
            return "non-extracted field results require a null value"
        return None

    def _legacy_value(self) -> object | None:
        """Return the legacy value attribute."""
        return self.field_value


_VALUE_ATTRIBUTE = "value"
setattr(FieldResult, _VALUE_ATTRIBUTE, property(FieldResult._legacy_value))
