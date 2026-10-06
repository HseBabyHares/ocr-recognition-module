#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSIONS = ROOT / "tools/container/versions.json"
SECURITY_INSTALLER = ROOT / "tools/security/install.py"


def load_security_installer():
    # The package self-test must be repeatable and must not leave __pycache__ in the distributable tree.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(
        "fadd_security_install", SECURITY_INSTALLER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load shared verified release installer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def install_disl(tool: dict, prefix: Path, dry_run: bool) -> dict:
    version = tool["version"]
    if dry_run:
        return {
            "tool": "docker-image-size-limit",
            "command": "disl",
            "version": version,
            "status": "planned",
            "source": "PyPI isolated venv",
        }
    env_dir = prefix / "venvs" / f"docker-image-size-limit-{version}"
    shutil.rmtree(env_dir, ignore_errors=True)
    venv.EnvBuilder(with_pip=True).create(env_dir)
    python = env_dir / "bin" / "python"
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            f"{tool['package']}=={version}",
        ],
        check=True,
    )
    source = env_dir / "bin" / "disl"
    if not source.exists():
        raise RuntimeError(
            "docker-image-size-limit installation did not provide disl"
        )
    destination = prefix / "bin" / "disl"
    destination.unlink(missing_ok=True)
    destination.symlink_to(source)
    return {
        "tool": "docker-image-size-limit",
        "command": "disl",
        "version": version,
        "status": "installed",
        "source": "PyPI isolated venv",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install pinned container delivery tools."
    )
    parser.add_argument(
        "--prefix",
        type=Path,
        default=Path.home() / ".local/omp-fadd/container",
    )
    parser.add_argument("--tool", action="append")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tools = json.loads(VERSIONS.read_text(encoding="utf-8"))["tools"]
    names = args.tool or list(tools)
    unknown = sorted(set(names) - set(tools))
    if unknown:
        print(
            json.dumps(
                {
                    "schemaVersion": "1.1",
                    "status": "blocked",
                    "error": f"unknown tools: {unknown}",
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2

    prefix = args.prefix.expanduser().resolve()
    if not args.dry_run:
        (prefix / "bin").mkdir(parents=True, exist_ok=True)
        (prefix / "venvs").mkdir(parents=True, exist_ok=True)

    records = []
    try:
        release_installer = load_security_installer()
        for name in names:
            tool = tools[name]
            if name == "docker-image-size-limit":
                records.append(install_disl(tool, prefix, args.dry_run))
            else:
                record = release_installer.install_binary(
                    name, tool, prefix, args.dry_run
                )
                record["command"] = tool["command"]
                records.append(record)
        result = {
            "schemaVersion": "1.1",
            "status": "planned" if args.dry_run else "installed",
            "prefix": str(prefix),
            "records": records,
        }
        if not args.dry_run:
            (prefix / "install-manifest.json").write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
        print(json.dumps(result, indent=2))
        return 0
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(
            json.dumps(
                {
                    "schemaVersion": "1.1",
                    "status": "blocked",
                    "error": str(error),
                    "records": records,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
