"""Validated workload role values for SPIFFE authorization."""

from __future__ import annotations

from enum import EnumType, StrEnum
from typing import Any, cast

from sird_workflow.spiffe._errors import UnknownWorkloadRoleError


class _WorkloadRoleType(EnumType):
    """Enum metaclass with validated workload role construction."""


def _workload_role_call(
    metaclass: EnumType,
    role_value: Any = None,
    **options: Any,
) -> Any:
    role_label = options.pop("role_label", role_value)
    role_label = options.pop("value", role_label)
    names = options.get("names")
    if names is not None:
        return EnumType.__call__(metaclass, role_label, **options)
    if options:
        raise TypeError("unexpected workload role arguments")
    if not isinstance(role_label, str) or not role_label:
        raise UnknownWorkloadRoleError("workload role must not be empty")
    if role_label != role_label.strip() or any(
        character.isspace() for character in role_label
    ):
        raise UnknownWorkloadRoleError(
            "workload role must not contain whitespace"
        )
    try:
        return EnumType.__call__(metaclass, role_label)
    except ValueError:
        dynamic_role = cast(
            Any,
            str.__new__(cast(type[str], metaclass), role_label),
        )
        dynamic_role._name_ = role_label
        dynamic_role._value_ = role_label
        value_map = metaclass._value2member_map_
        value_map[role_label] = dynamic_role
        return dynamic_role


type.__setattr__(_WorkloadRoleType, "__call__", _workload_role_call)


class WorkloadRole(StrEnum, metaclass=_WorkloadRoleType):
    """A non-empty, stable role label used by an authorization policy."""

    TASK_SERVICE = "task-service"
    PROCESS_SERVICE = "process-service"
    OCR_SERVICE = "ocr-service"
    SIRD_BACKEND = "sird-backend"
