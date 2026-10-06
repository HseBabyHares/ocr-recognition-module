#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
errors = []
counts = {"python": 0, "javascript": 0, "shell": 0, "json": 0, "yaml": 0}
for p in ROOT.rglob("*"):
    if not p.is_file() or any(
        x in p.parts
        for x in [
            "artifacts",
            ".git",
            ".cache",
            ".venv",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "dist",
        ]
    ):
        continue
    try:
        if p.suffix == ".py":
            compile(p.read_text(encoding="utf-8"), str(p), "exec")
            counts["python"] += 1
        elif p.suffix in {".js", ".mjs"}:
            r = subprocess.run(
                ["node", "--check", str(p)], capture_output=True, text=True
            )
            counts["javascript"] += 1
            if r.returncode:
                errors.append(f"{p}: {r.stderr}")
        elif p.suffix == ".sh":
            r = subprocess.run(
                ["bash", "-n", str(p)], capture_output=True, text=True
            )
            counts["shell"] += 1
            if r.returncode:
                errors.append(f"{p}: {r.stderr}")
        elif p.suffix == ".json":
            json.loads(p.read_text())
            counts["json"] += 1
    except Exception as e:
        errors.append(f"{p}: {e}")
try:
    import yaml

    for p in list(ROOT.rglob("*.yml")) + list(ROOT.rglob("*.yaml")):
        yaml.safe_load(p.read_text())
        counts["yaml"] += 1
except ImportError:
    pass
print(
    json.dumps(
        {
            "check": "syntax",
            "status": "fail" if errors else "pass",
            "counts": counts,
            "errors": errors,
        },
        indent=2,
    )
)
sys.exit(1 if errors else 0)
