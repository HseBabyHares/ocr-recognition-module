from __future__ import annotations

from pathlib import Path

from sird_verification.contracts import OracleStatus
from sird_verification.oracles import architecture_boundary_oracle

FORBIDDEN_IMPORTS_KEY = "forbidden_imports"
NO_FORBIDDEN_IMPORTS = 0
EXPECTED_FORBIDDEN_IMPORTS = 2


def test_root_has_no_forbidden_import_edges() -> None:
    recognition_package = Path(__file__).resolve().parents[2] / "src" / "sird_recognition"

    oracle_result = architecture_boundary_oracle(recognition_package)

    assert oracle_result.status is OracleStatus.PASS
    assert oracle_result.observed["files_inspected"] > NO_FORBIDDEN_IMPORTS
    assert oracle_result.observed[FORBIDDEN_IMPORTS_KEY] == NO_FORBIDDEN_IMPORTS


def test_boundary_failure_and_blocked(tmp_path: Path) -> None:
    package = tmp_path / "sird_recognition"
    package.mkdir()
    (package / "bad.py").write_text(
        "import os, sqlalchemy\nfrom sird_workflow import service\n",
        encoding="utf-8",
    )

    failure = architecture_boundary_oracle(package)
    missing = architecture_boundary_oracle(tmp_path / "missing")

    assert failure.status is OracleStatus.FAIL
    assert failure.observed[FORBIDDEN_IMPORTS_KEY] == EXPECTED_FORBIDDEN_IMPORTS
    assert missing.status is OracleStatus.BLOCKED
