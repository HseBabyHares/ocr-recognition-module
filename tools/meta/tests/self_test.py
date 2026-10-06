#!/usr/bin/env python3
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
r = subprocess.run(
    [sys.executable, str(ROOT / "tools/meta/install.py"), "--dry-run"],
    capture_output=True,
    text=True,
)
assert r.returncode == 0, (r.stdout, r.stderr)
with tempfile.TemporaryDirectory() as td:
    env = {**os.environ, "PATH": "/usr/bin:/bin"}
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools/meta/preflight.py"), "--strict"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
print('{"check":"meta-harness","status":"pass"}')
