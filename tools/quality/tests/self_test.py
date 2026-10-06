#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td)
    policy = td / "policy.json"
    p = json.loads((ROOT / "tools/quality/policy.example.json").read_text())
    p["status"] = "active"
    policy.write_text(json.dumps(p))
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/quality/complexity.py"),
            "--policy",
            str(policy),
            str(ROOT / "tools/quality/tests/fixtures/bad.py"),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1, (r.stdout, r.stderr)
    assert json.loads(r.stdout)["findings"]
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools/quality/install.py"), "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)

    inactive = td / "inactive.json"
    q = dict(p)
    q["status"] = "template-unconfigured"
    inactive.write_text(json.dumps(q))
    out = td / "out"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/quality/run.py"),
            "--repo",
            str(td),
            "--policy",
            str(inactive),
            "--out",
            str(out),
            "--advisory",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert (
        json.loads((out / "summary.json").read_text())["status"]
        == "not-configured"
    )
    # Missing toolchain is BLOCKED rather than PASS.
    env = {**os.environ, "PATH": "/usr/bin:/bin"}
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools/quality/preflight.py"), "--strict"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2, (r.stdout, r.stderr)
print('{"check":"quality-harness","status":"pass"}')
