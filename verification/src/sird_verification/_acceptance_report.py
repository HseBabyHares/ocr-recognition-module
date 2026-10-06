"""Assembly helpers for the stable acceptance report."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import MappingProxyType

from sird_verification import _acceptance_status as _status

STATUS = str
Row = dict[str, object]
Rows = list[Row]
RowsById = dict[str, Row]
Acceptance = dict[str, Row]
SectionIds = tuple[str, ...]
Section = tuple[str, SectionIds, STATUS, str]
Sections = tuple[Section, ...]
RunSpec = Callable[..., tuple[STATUS, str]]

PYTEST_COMMAND = "pytest"
_ORACLE_TEST_MODULE = "verification/tests/test_recognition_oracles.py"
_CANDIDATE_ORACLE_LOCATION = (
    f"{_ORACLE_TEST_MODULE}::test_candidate_refusal"
)
_SELECTOR_ORACLE_LOCATION = (
    f"{_ORACLE_TEST_MODULE}::test_selector_rejection"
)
_PARTIAL_FIELD_ORACLE_LOCATION = f"{_ORACLE_TEST_MODULE}::test_partial_fields"

@dataclass(frozen=True, slots=True)
class OracleSpec:
    location: str | None
    command: tuple[str, ...] | None
    reason: str


@dataclass(frozen=True, slots=True)
class ReportInputs:
    test_ids: tuple[str, ...]
    oracles: Mapping[str, OracleSpec]
    required_ids: SectionIds
    second_ids: SectionIds
    third_ids: SectionIds

ORACLES: Mapping[str, OracleSpec] = MappingProxyType(
    {
        "TEST-OCR-003": OracleSpec(
            (_CANDIDATE_ORACLE_LOCATION,),
            (PYTEST_COMMAND, _CANDIDATE_ORACLE_LOCATION),
            "zero-candidate refusal oracle executed",
        ),
        "TEST-OCR-004": OracleSpec(
            (_CANDIDATE_ORACLE_LOCATION,),
            (PYTEST_COMMAND, _CANDIDATE_ORACLE_LOCATION),
            "candidate refusal oracle executed",
        ),
        "TEST-OCR-005": OracleSpec(
            (_SELECTOR_ORACLE_LOCATION,),
            (PYTEST_COMMAND, _SELECTOR_ORACLE_LOCATION),
            "strict selector rejection oracle executed",
        ),
        "TEST-OCR-014": OracleSpec(
            (_PARTIAL_FIELD_ORACLE_LOCATION,),
            (PYTEST_COMMAND, _PARTIAL_FIELD_ORACLE_LOCATION),
            "partial-field preservation oracle executed",
        ),
    },
)


def _row_for_test(
    test_id: str,
    *,
    cwd: Path,
    oracles: Mapping[str, OracleSpec],
    run_spec: RunSpec,
) -> Row:
    spec = oracles.get(test_id)
    if spec is None:
        status, details, location = (
            _status.BLOCKED_STATUS,
            "ID-specific executable oracle is not registered",
            None,
        )
    else:
        status, details = run_spec(spec, cwd=cwd)
        location = spec.location
    return {
        "id": test_id,
        _status.STATUS_KEY: status,
        "oracle": location,
        "evidence": location,
        "observed": details,
    }


def _acceptance_from_sections(sections: Sections) -> Acceptance:
    acceptance: Acceptance = {}
    for key, ids, status, reason in sections:
        acceptance[key] = {
            _status.STATUS_KEY: status,
            "ids": list(ids),
            "reason": reason,
        }
    return acceptance


def _build_acceptance(
    rows_by_id: Mapping[str, Row],
    required_ids: SectionIds,
    second_ids: SectionIds,
    third_ids: SectionIds,
) -> Acceptance:
    required_statuses = _status._required_statuses(
        rows_by_id,
        required_ids,
    )
    first_status = _status.acceptance_status(required_statuses)
    first_reason = (
        "all AC-OCR-001 IDs passed"
        if first_status == _status.PASSED_STATUS
        else " ".join(
            (
                "AC-OCR-001 cannot pass while any required ID is",
                "blocked, not_run, or failed",
            ),
        )
    )
    sections: Sections = (
        ("AC-OCR-001", required_ids, first_status, first_reason),
        (
            "AC-OCR-002",
            second_ids,
            _status.BLOCKED_STATUS,
            " ".join(
                (
                    "AC-OCR-002 requires protected corpus, predeclared",
                    "numeric boundaries, and independent resource evidence",
                ),
            ),
        ),
        (
            "AC-OCR-003",
            third_ids,
            _status.BLOCKED_STATUS,
            " ".join(
                (
                    "AC-OCR-003 requires protected corpus, replay evidence,",
                    "and independent metric recomputation",
                ),
            ),
        ),
    )
    return _acceptance_from_sections(sections)


def _build_command(rows: Rows) -> dict[str, str]:
    return {
        "command": " ".join(
            (
                "uv run --project verification --group dev",
                "python -m sird_verification.acceptance_runner",
            ),
        ),
        _status.STATUS_KEY: _status.command_status(rows),
        "observed": " ".join(
            (
                "stable IDs evaluated with distinct failed",
                "and blocked states",
            ),
        ),
    }


def build_report(
    *,
    cwd: Path,
    inputs: ReportInputs,
    run_spec: RunSpec,
) -> dict[str, object]:
    rows = [
        _row_for_test(
            test_id,
            cwd=cwd,
            oracles=inputs.oracles,
            run_spec=run_spec,
        )
        for test_id in inputs.test_ids
    ]
    rows_by_id: RowsById = {str(row["id"]): row for row in rows}
    return {
        "schema_version": "1.0",
        "generated_at": date.today().isoformat(),
        "scope": "AC-OCR-001..003",
        "commands": [_build_command(rows)],
        "test_cases": rows,
        "acceptance": _build_acceptance(
            rows_by_id,
            inputs.required_ids,
            inputs.second_ids,
            inputs.third_ids,
        ),
    }
