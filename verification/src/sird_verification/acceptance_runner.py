"""Stable-ID acceptance runner for AC-OCR-001."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from sird_verification import _acceptance_ids as _ids
from sird_verification import _acceptance_report as _report
from sird_verification import _acceptance_status as _status


STATUS_KEY = _status.STATUS_KEY
PASSED_STATUS = _status.PASSED_STATUS
FAILED_STATUS = _status.FAILED_STATUS
BLOCKED_STATUS = _status.BLOCKED_STATUS
NOT_RUN_STATUS = _status.NOT_RUN_STATUS
STATUSES = _status.STATUSES
FIRST_TEST_NUMBER = _ids.FIRST_TEST_NUMBER
LAST_TEST_NUMBER = _ids.LAST_TEST_NUMBER
TEST_ID_PREFIX = _ids.TEST_ID_PREFIX
PYTEST_COMMAND = _report.PYTEST_COMMAND
ALL_TEST_IDS = _ids.ALL_TEST_IDS
AC_OCR_ONE_NUMBERS = _ids.AC_OCR_ONE_NUMBERS
AC_OCR_ONE_IDS = _ids.AC_OCR_ONE_IDS
AC_OCR_TWO_IDS = _ids.AC_OCR_TWO_IDS
AC_OCR_THREE_IDS = _ids.AC_OCR_THREE_IDS
TEST_IDS = ALL_TEST_IDS

OracleSpec = _report.OracleSpec
ORACLES = _report.ORACLES


def _report_inputs() -> _report.ReportInputs:
    return _report.ReportInputs(
        test_ids=TEST_IDS,
        oracles=ORACLES,
        required_ids=AC_OCR_ONE_IDS,
        second_ids=AC_OCR_TWO_IDS,
        third_ids=AC_OCR_THREE_IDS,
    )


def _run_spec(spec: _report.OracleSpec, *, cwd: Path) -> tuple[str, str]:
    if spec.command is None or spec.location is None:
        return _status.BLOCKED_STATUS, spec.reason
    command = spec.command
    if cwd.name == "verification":
        command = tuple(
            part.removeprefix("verification/") for part in command
        )
    completed = subprocess.run(
        [sys.executable, "-m", *command],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return _status.PASSED_STATUS, spec.reason
    return _status.FAILED_STATUS, f"oracle command exited with {completed.returncode}"


def build_report(*, cwd: Path | None = None) -> dict[str, object]:
    root = cwd or Path.cwd()
    inputs = _report_inputs()
    return _report.build_report(
        cwd=root,
        inputs=inputs,
        run_spec=_run_spec,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/acceptance/report.json"),
    )
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    serialized_report = json.dumps(report, indent=2)
    args.output.write_text(
        "{0}\n".format(serialized_report),
        encoding="utf-8",
    )
    command_status = report["commands"][0][_status.STATUS_KEY]
    return int(command_status == "fail")


if __name__ == "__main__":
    sys.exit(main())
