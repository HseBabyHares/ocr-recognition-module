from __future__ import annotations

import sys
from functools import partial

from sird_verification import acceptance_runner as runner
from sird_verification.acceptance_runner import (
    AC_OCR_ONE_IDS,
    AC_OCR_TWO_IDS,
    AC_OCR_THREE_IDS,
    TEST_IDS,
    OracleSpec,
    build_report,
)

EXPECTED_TEST_CASE_COUNT = 25
STATUS_KEY = "status"
TEST_CASES_KEY = "test_cases"
ACCEPTANCE_KEY = "acceptance"
COMMANDS_KEY = "commands"
BLOCKED_STATUS = "blocked"
FAIL_STATUS = "fail"
FAILED_STATUS = "failed"
PASSED_STATUS = "passed"


def _oracle_failure(spec, *, failure_ids, **_kwargs):
    if failure_ids is None:
        return FAILED_STATUS, "injected oracle failure"
    if spec.location in failure_ids:
        return FAILED_STATUS, "injected experiment failure"
    return PASSED_STATUS, "injected contract pass"


def test_report_has_stable_ids_and_schema() -> None:
    report = build_report()
    rows = report[TEST_CASES_KEY]
    assert [row["id"] for row in rows] == list(TEST_IDS)
    assert len(rows) == EXPECTED_TEST_CASE_COUNT
    assert all(
        row[STATUS_KEY]
        in {PASSED_STATUS, FAILED_STATUS, BLOCKED_STATUS, "not_run"}
        for row in rows
    )
    assert all(
        row["oracle"] or row[STATUS_KEY] == BLOCKED_STATUS for row in rows
    )
    assert all("observed" in row for row in rows)


def test_blocked_ids_never_pass_acceptance() -> None:
    report = build_report()
    statuses = {row[STATUS_KEY] for row in report[TEST_CASES_KEY]}
    assert BLOCKED_STATUS in statuses
    assert report[ACCEPTANCE_KEY]["AC-OCR-001"][STATUS_KEY] == BLOCKED_STATUS
    assert report[ACCEPTANCE_KEY]["AC-OCR-002"][STATUS_KEY] == BLOCKED_STATUS
    assert report[ACCEPTANCE_KEY]["AC-OCR-002"]["ids"] == list(AC_OCR_TWO_IDS)


def test_failed_oracle_fails_acceptance(monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "_run_spec",
        partial(_oracle_failure, failure_ids=None),
    )
    report = runner.build_report()

    assert report[COMMANDS_KEY][0][STATUS_KEY] == FAIL_STATUS
    assert report[ACCEPTANCE_KEY]["AC-OCR-001"][STATUS_KEY] == FAILED_STATUS


def test_experiment_failure_blocks_ac1(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        runner,
        "ORACLES",
        {
            test_id: OracleSpec(test_id, ("pytest", test_id), test_id)
            for test_id in TEST_IDS
        },
    )

    experiment_only_ids = set(AC_OCR_THREE_IDS) - set(AC_OCR_ONE_IDS)
    monkeypatch.setattr(
        runner,
        "_run_spec",
        partial(_oracle_failure, failure_ids=experiment_only_ids),
    )
    report = runner.build_report(cwd=tmp_path)

    assert report[COMMANDS_KEY][0][STATUS_KEY] == FAIL_STATUS
    assert report[ACCEPTANCE_KEY]["AC-OCR-001"][STATUS_KEY] == PASSED_STATUS
    assert report[ACCEPTANCE_KEY]["AC-OCR-003"][STATUS_KEY] == BLOCKED_STATUS


def test_experiment_failure_exits_one(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        runner,
        "ORACLES",
        {
            test_id: OracleSpec(test_id, ("pytest", test_id), test_id)
            for test_id in TEST_IDS
        },
    )
    monkeypatch.setattr(
        runner,
        "_run_spec",
        partial(_oracle_failure, failure_ids=set(AC_OCR_THREE_IDS)),
    )
    output = tmp_path / "report.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["acceptance_runner", "--output", str(output)],
    )

    assert runner.main() == 1
