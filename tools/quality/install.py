#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "tools/quality/toolchain.lock.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--prefix", type=Path, default=Path.home() / ".local/omp-fadd/quality"
    )
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    lock = json.loads(LOCK.read_text())
    prefix = a.prefix.expanduser().resolve()
    packages = [f"{k}=={v}" for k, v in lock["packages"].items()]
    if a.dry_run:
        print(
            json.dumps(
                {
                    "schemaVersion": "1.0",
                    "status": "planned",
                    "prefix": str(prefix),
                    "packages": packages,
                },
                indent=2,
            )
        )
        return 0
    env = prefix / "venv"
    shutil.rmtree(env, ignore_errors=True)
    venv.EnvBuilder(with_pip=True).create(env)
    python = env / "bin" / "python"
    try:
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                *packages,
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(
            json.dumps({"status": "blocked", "error": str(e)}, indent=2),
            file=sys.stderr,
        )
        return 2
    (prefix / "bin").mkdir(parents=True, exist_ok=True)
    for command in [
        "ruff",
        "flake8",
        "mypy",
        "lint-imports",
        "pytest",
        "coverage",
        "diff-cover",
        "mutmut",
        "disl",
    ]:
        source = env / "bin" / command
        if source.exists():
            dest = prefix / "bin" / command
            dest.unlink(missing_ok=True)
            dest.symlink_to(source)
    result = {
        "schemaVersion": "1.0",
        "status": "installed",
        "prefix": str(prefix),
        "packages": lock["packages"],
    }
    (prefix / "install-manifest.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
