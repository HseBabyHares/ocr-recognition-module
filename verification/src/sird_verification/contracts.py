"""Typed outcomes shared by executable verification oracles."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class OracleStatus(StrEnum):
    """Outcome of one oracle execution."""

    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


@dataclass(frozen=True, slots=True)
class OracleResult:
    """Stable, explicit evidence from one verification oracle.

    ``observed`` contains bounded, non-sensitive facts.  Oracles must not put
    request payloads, capability tokens, document content, or exception text
    in this record.
    """

    oracle_id: str
    status: OracleStatus
    observed: Mapping[str, Any]
    reason: str

    def __post_init__(self) -> None:
        if not self.oracle_id.strip():
            raise ValueError("oracle_id must be non-empty")
        if not self.reason.strip():
            raise ValueError("reason must be non-empty")
        object.__setattr__(
            self,
            "observed",
            MappingProxyType(dict(self.observed)),
        )

    @property
    def evidence(self) -> Mapping[str, Any]:
        """Alias for callers that name the observed evidence field."""

        return self.observed

    @property
    def passed(self) -> bool:
        """Whether this oracle proved its contract."""

        return self.status is OracleStatus.PASS

    @property
    def terminal(self) -> bool:
        """Whether the oracle reached an outcome instead of being skipped."""

        return self.status in {OracleStatus.PASS, OracleStatus.FAIL}
