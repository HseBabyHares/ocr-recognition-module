#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]

result = subprocess.run(
    [sys.executable, str(ROOT / "tools/container/install.py"), "--dry-run"],
    capture_output=True,
    text=True,
)
assert result.returncode == 0, (result.stdout, result.stderr)
plan = json.loads(result.stdout)
assert plan["status"] == "planned"
assert {item["tool"] for item in plan["records"]} == {
    "hadolint",
    "dive",
    "syft",
    "docker-image-size-limit",
}
assert all(item["status"] == "planned" for item in plan["records"])

with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td)
    repo = td / "repo"
    repo.mkdir()
    out = td / "out"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/container/check.py"),
            "--repo",
            str(repo),
            "--out",
            str(out),
            "--advisory",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert (
        json.loads((out / "summary.json").read_text())["status"]
        == "not-configured"
    )
    env = {**os.environ, "PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/container/preflight.py"),
            "--strict",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2

print('{"check":"container-harness","status":"pass"}')
