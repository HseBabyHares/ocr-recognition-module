#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def execute(name: str, command: list[str], cwd: Path, out: Path) -> dict:
    try:
        result = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True
        )
        status = "pass" if result.returncode == 0 else "fail"
        text = (result.stdout or "") + (result.stderr or "")
        code = result.returncode
    except FileNotFoundError as error:
        status = "blocked"
        text = str(error)
        code = 127
    log = out / f"{name}.log"
    log.write_text(text, encoding="utf-8")
    return {
        "check": name,
        "command": command,
        "exitCode": code,
        "status": status,
        "log": str(log),
    }


def write_summary(out: Path, result: dict) -> None:
    (out / "summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--out", type=Path, default=Path("quality-reports"))
    parser.add_argument("--advisory", action="store_true")
    args = parser.parse_args()

    repo = args.repo.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    policy_path = args.policy or repo / "quality/python-policy.json"

    if not policy_path.exists():
        result = {
            "schemaVersion": "1.1",
            "status": "not-configured",
            "reason": str(policy_path),
            "checks": [],
        }
        write_summary(out, result)
        return 0 if args.advisory else 2

    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if policy.get("status") != "active":
        result = {
            "schemaVersion": "1.1",
            "status": "not-configured",
            "policyStatus": policy.get("status"),
            "checks": [],
        }
        write_summary(out, result)
        return 0 if args.advisory else 2

    paths = [
        item
        for item in policy.get("pythonPaths", [])
        if (repo / item).exists()
    ]
    if not paths:
        result = {
            "schemaVersion": "1.1",
            "status": "not-applicable",
            "checks": [],
        }
        write_summary(out, result)
        return 0

    preflight = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/quality/preflight.py"),
            "--strict",
            "--out",
            str(out / "preflight.json"),
        ],
        cwd=repo,
    )
    if preflight.returncode:
        result = {
            "schemaVersion": "1.1",
            "status": "blocked",
            "reason": "quality-toolchain-preflight",
            "checks": [],
        }
        write_summary(out, result)
        return 0 if args.advisory else 2

    checks = [
        execute(
            "ruff-format", ["ruff", "format", "--check", *paths], repo, out
        ),
        execute("ruff-check", ["ruff", "check", *paths], repo, out),
        execute("wps", ["flake8", "--select=WPS,E999", *paths], repo, out),
        execute(
            "mypy",
            ["mypy", "--strict", *policy.get("mypyPaths", paths)],
            repo,
            out,
        ),
        execute(
            "complexity",
            [
                sys.executable,
                str(ROOT / "tools/quality/complexity.py"),
                "--policy",
                str(policy_path),
                "--out",
                str(out / "complexity.json"),
                *paths,
            ],
            repo,
            out,
        ),
    ]

    pyproject = repo / "pyproject.toml"
    if (repo / ".importlinter").exists() or (
        pyproject.exists()
        and "[tool.importlinter]"
        in pyproject.read_text(encoding="utf-8", errors="ignore")
    ):
        checks.append(execute("import-linter", ["lint-imports"], repo, out))

    test_paths = policy.get("testPaths") or []
    if test_paths and all((repo / item).exists() for item in test_paths):
        checks.append(
            execute(
                "pytest-coverage",
                [
                    "coverage",
                    "run",
                    "--branch",
                    "-m",
                    "pytest",
                    "--strict-config",
                    "--strict-markers",
                    *test_paths,
                ],
                repo,
                out,
            )
        )
        if checks[-1]["status"] == "pass":
            coverage = policy.get("coverage") or {}
            report_cmd = ["coverage", "report"]
            minimum = coverage.get("minimumOverallPercent")
            if minimum is not None:
                report_cmd.extend(["--fail-under", str(minimum)])
            checks.append(execute("coverage-report", report_cmd, repo, out))
            checks.append(
                execute(
                    "coverage-xml",
                    ["coverage", "xml", "-o", str(out / "coverage.xml")],
                    repo,
                    out,
                )
            )
            base = os.environ.get("BASE_SHA")
            changed_minimum = coverage.get("minimumChangedPercent")
            if (
                base
                and changed_minimum is not None
                and checks[-1]["status"] == "pass"
            ):
                checks.append(
                    execute(
                        "diff-cover",
                        [
                            "diff-cover",
                            str(out / "coverage.xml"),
                            "--compare-branch",
                            base,
                            "--fail-under",
                            str(changed_minimum),
                        ],
                        repo,
                        out,
                    )
                )

    status = (
        "blocked"
        if any(item["status"] == "blocked" for item in checks)
        else "fail"
        if any(item["status"] == "fail" for item in checks)
        else "pass"
    )
    result = {"schemaVersion": "1.1", "status": status, "checks": checks}
    write_summary(out, result)
    if args.advisory:
        return 0
    return {"pass": 0, "fail": 1, "blocked": 2}[status]


if __name__ == "__main__":
    raise SystemExit(main())
