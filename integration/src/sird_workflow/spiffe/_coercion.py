"""Private SPIFFE parsing and coercion helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import SplitResult, urlsplit

from sird_workflow.spiffe._errors import (
    InvalidCredentialError,
    MalformedSpiffeIdError,
    UnknownWorkloadRoleError,
)

_MALFORMED_SPIFFE_ID = "SPIFFE identity is malformed"


def coerce_spiffe_id(candidate: object):
    from sird_workflow.spiffe._identity import SpiffeId

    if isinstance(candidate, SpiffeId):
        return candidate
    if isinstance(candidate, str):
        return SpiffeId(candidate)
    raise MalformedSpiffeIdError("workload identity has an invalid type")


def coerce_role(candidate: object):
    from sird_workflow.spiffe._role import WorkloadRole

    if isinstance(candidate, WorkloadRole):
        return candidate
    if isinstance(candidate, str):
        return WorkloadRole(candidate)
    raise UnknownWorkloadRoleError("workload role has an invalid type")


def coerce_now(candidate: datetime | None) -> datetime:
    current = datetime.now(UTC) if candidate is None else candidate
    validate_timestamp(current, "validation time")
    return current


def validate_timestamp(timestamp: object, label: str) -> None:
    if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
        raise InvalidCredentialError(f"{label} must be timezone-aware")


def parse_spiffe_id(identifier: str) -> tuple[str, str]:
    if (
        not isinstance(identifier, str)
        or not identifier
        or identifier != identifier.strip()
    ):
        raise MalformedSpiffeIdError(_MALFORMED_SPIFFE_ID)
    try:
        parsed = urlsplit(identifier)
    except (UnicodeError, ValueError):
        raise MalformedSpiffeIdError(_MALFORMED_SPIFFE_ID) from None
    _validate_spiffe_parts(parsed)
    return parsed.netloc, parsed.path


def _validate_spiffe_parts(parsed: SplitResult) -> None:
    try:
        endpoint = parsed.hostname, parsed.port
    except (UnicodeError, ValueError):
        raise MalformedSpiffeIdError(_MALFORMED_SPIFFE_ID) from None
    hostname, port = endpoint
    if _invalid_spiffe_parts(parsed, hostname, port):
        raise MalformedSpiffeIdError(_MALFORMED_SPIFFE_ID)


def _invalid_spiffe_parts(
    parsed: SplitResult, hostname: str | None, port: int | None
) -> bool:
    structural_checks = (
        parsed.scheme != "spiffe",
        not parsed.netloc,
        hostname is None,
        parsed.username is not None,
        parsed.password is not None,
        port is not None,
        bool(parsed.query),
        bool(parsed.fragment),
        not parsed.path,
        parsed.path == "/",
        any(character.isspace() for character in parsed.netloc + parsed.path),
    )
    return any(structural_checks)
