#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "tools/security/toolchain.lock.json"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )


def semantic_version(text: str) -> str | None:
    match = re.search(r"\b\d+\.\d+\.\d+\b", text)
    return match.group(0) if match else None


def inspect_command(
    name: str,
    spec: dict[str, Any],
    command: str | None,
) -> dict[str, Any]:
    if not command:
        return {
            "tool": name,
            "command": None,
            "expected": spec["version"],
            "observed": None,
            "status": "missing",
            "versionSource": None,
            "raw": "",
        }

    cli_result = run([command, *spec["versionArgs"]])
    cli_raw = (cli_result.stdout + cli_result.stderr).strip()
    cli_observed = semantic_version(cli_raw)
    observed = cli_observed
    version_source = "cli"

    if spec.get("install") == "python-venv" and spec.get("package"):
        resolved = Path(command).resolve()
        python = resolved.parent / "python"
        if python.is_file():
            metadata_result = run(
                [
                    str(python),
                    "-c",
                    (
                        "import importlib.metadata;"
                        f"print(importlib.metadata.version({spec['package']!r}))"
                    ),
                ]
            )
            if metadata_result.returncode == 0:
                distribution_version = metadata_result.stdout.strip()
                if semantic_version(distribution_version):
                    observed = distribution_version
                    version_source = "python-distribution"

    status = (
        "ok"
        if cli_result.returncode == 0 and observed == spec["version"]
        else "version-mismatch"
    )
    return {
        "tool": name,
        "command": command,
        "expected": spec["version"],
        "observed": observed,
        "cliObserved": cli_observed,
        "status": status,
        "versionSource": version_source,
        "raw": cli_raw[:500],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--out", type=Path)
    arguments = parser.parse_args()
    specs = json.loads(LOCK.read_text(encoding="utf-8"))["tools"]
    rows = [
        inspect_command(name, spec, shutil.which(spec["command"]))
        for name, spec in specs.items()
    ]
    result = {
        "schemaVersion": "1.0",
        "status": (
            "pass" if all(row["status"] == "ok" for row in rows) else "blocked"
        ),
        "tools": rows,
    }
    text = json.dumps(result, indent=2) + "\n"
    print(text, end="")
    if arguments.out:
        arguments.out.parent.mkdir(parents=True, exist_ok=True)
        arguments.out.write_text(text, encoding="utf-8")
    return 0 if result["status"] == "pass" or not arguments.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
