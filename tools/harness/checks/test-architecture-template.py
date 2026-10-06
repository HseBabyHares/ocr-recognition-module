#!/usr/bin/env python3
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory() as td:
    shutil.copytree(ROOT / "templates/repository", td, dirs_exist_ok=True)
    policy = pathlib.Path(td) / "architecture/policy.json"
    import json

    data = json.loads(policy.read_text())
    data["status"] = "active"
    policy.write_text(json.dumps(data, indent=2) + "\n")
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/architecture/validate.py"),
            "--repo",
            td,
            "--policy",
            "architecture/policy.json",
            "--mode",
            "strict",
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise SystemExit(1)
print('{"check":"architecture-template","status":"pass"}')
