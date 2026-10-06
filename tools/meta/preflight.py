#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    specs = json.loads((ROOT / "tools/meta/toolchain.lock.json").read_text())[
        "tools"
    ]
    rows = []
    for name, spec in specs.items():
        exe = shutil.which(spec["command"])
        raw = ""
        observed = None
        status = "missing"
        if exe:
            r = subprocess.run(
                [exe, "--version"], capture_output=True, text=True
            )
            raw = (r.stdout + r.stderr).strip()
            m = re.search(r"\b\d+\.\d+(?:\.\d+)?\b", raw)
            observed = m.group(0) if m else None
            status = (
                "ok"
                if r.returncode == 0 and observed == spec["version"]
                else "version-mismatch"
            )
        rows.append(
            {
                "tool": name,
                "path": exe,
                "expected": spec["version"],
                "observed": observed,
                "status": status,
                "raw": raw[:500],
            }
        )
    result = {
        "schemaVersion": "1.0",
        "status": "pass"
        if all(x["status"] == "ok" for x in rows)
        else "blocked",
        "tools": rows,
    }
    text = json.dumps(result, indent=2) + "\n"
    print(text, end="")
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text)
    return 0 if result["status"] == "pass" or not a.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
