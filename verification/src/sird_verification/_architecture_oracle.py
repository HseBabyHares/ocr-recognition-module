"""Executable architecture boundary oracle."""

from __future__ import annotations

from pathlib import Path

from sird_verification._architecture_scan import scan
from sird_verification.contracts import OracleStatus
from sird_verification._oracle_support import (
    blocked,
    build_result,
    resolve_recognition_root,
)

_ARCHITECTURE_ORACLE_ID = "architecture.root-import-boundary"
_FORBIDDEN_IMPORTS = (
    "broker",
    "confluent_kafka",
    "database",
    "db",
    "kafka",
    "psycopg",
    "sqlalchemy",
    "sird_workflow",
    "workflow",
)


def architecture_boundary_oracle(root: str | Path | None = None) -> OracleResult:
    """Inspect root OCR imports for forbidden workflow, database, or broker edges."""
    package_root = resolve_recognition_root(root)
    if package_root is None or not package_root.is_dir():
        return blocked(
            _ARCHITECTURE_ORACLE_ID,
            "root recognition source is unavailable",
        )
    files_inspected, violations, parse_failures = scan(
        package_root,
        _FORBIDDEN_IMPORTS,
    )
    observed = {
        "files_inspected": files_inspected,
        "forbidden_imports": len(violations),
        "parse_failures": parse_failures,
    }
    if parse_failures:
        return build_result(
            _ARCHITECTURE_ORACLE_ID,
            OracleStatus.FAIL,
            observed,
            "root recognition imports could not be inspected completely",
        )
    if violations:
        observed = {**observed, "violation_locations": violations}
        return build_result(
            _ARCHITECTURE_ORACLE_ID,
            OracleStatus.FAIL,
            observed,
            "root recognition imports cross a forbidden boundary",
        )
    return build_result(
        _ARCHITECTURE_ORACLE_ID,
        OracleStatus.PASS,
        observed,
        "root recognition imports have no forbidden workflow, database, or broker edges",
    )
