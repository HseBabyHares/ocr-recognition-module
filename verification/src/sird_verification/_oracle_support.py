"""Shared support for executable verification oracles."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sird_verification.contracts import OracleResult, OracleStatus


def build_result(
    oracle_id: str,
    status: OracleStatus,
    observed: Mapping[str, Any],
    reason: str,
) -> OracleResult:
    """Build one immutable oracle result."""
    return OracleResult(oracle_id, status, observed, reason)


def blocked(oracle_id: str, reason: str) -> OracleResult:
    """Report that the evidence needed by an oracle is unavailable."""
    return build_result(oracle_id, OracleStatus.BLOCKED, {}, reason)


def enum_value(candidate: Any, attribute: str) -> str | None:
    """Read either a plain value or an enum-valued attribute."""
    raw = getattr(candidate, attribute, None)
    return getattr(raw, "value", raw)


def is_ack_gate_error(error: Exception) -> bool:
    """Identify the workflow error for an unacknowledged publication."""
    try:
        from sird_workflow.dead_letter import PublicationNotAcknowledgedError
    except ImportError:
        return False
    return isinstance(error, PublicationNotAcknowledgedError)


def is_capability_rejection(error: Exception) -> bool:
    """Identify an artifact capability validation rejection."""
    try:
        from sird_workflow.artifact_security import ArtifactSecurityError
    except ImportError:
        return False
    return isinstance(error, ArtifactSecurityError)


def resolve_recognition_root(root: str | Path | None) -> Path | None:
    """Resolve the recognition package root used by the architecture oracle."""
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[3] / "src" / "sird_recognition"


def imported_modules(node: ast.AST) -> tuple[str, ...]:
    """Extract module names represented by one import AST node."""
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return (node.module,)
    if isinstance(node, ast.ImportFrom):
        return tuple(alias.name for alias in node.names)
    return ()
