#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(name, cmd, cwd, out, timeout=900):
    try:
        r = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        status = "pass" if r.returncode == 0 else "fail"
    except subprocess.TimeoutExpired as e:
        r = None
        status = "blocked"
        text = (e.stdout or "") + (e.stderr or "")
    else:
        text = (r.stdout or "") + (r.stderr or "")
    log = out / f"{name}.log"
    log.write_text(text)
    return {
        "check": name,
        "status": status,
        "exitCode": r.returncode if r else 124,
        "command": cmd,
        "log": str(log),
    }


def image_size(tag, cwd):
    r = subprocess.run(
        ["docker", "image", "inspect", tag, "--format", "{{.Size}}"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return (
        int(r.stdout.strip())
        if r.returncode == 0 and r.stdout.strip().isdigit()
        else None
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--policy", type=Path)
    ap.add_argument("--out", type=Path, default=Path("container-reports"))
    ap.add_argument("--image", action="append")
    ap.add_argument("--advisory", action="store_true")
    a = ap.parse_args()
    repo = a.repo.resolve()
    policy = a.policy or repo / "container/policy.json"
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not policy.exists():
        result = {"schemaVersion": "1.0", "status": "not-configured"}
        (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return 0 if a.advisory else 2
    p = json.loads(policy.read_text())
    if p.get("status") != "active":
        result = {
            "schemaVersion": "1.0",
            "status": "not-configured",
            "policyStatus": p.get("status"),
        }
        (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return 0 if a.advisory else 2
    pf = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/container/preflight.py"),
            "--strict",
            "--out",
            str(out / "preflight.json"),
        ],
        cwd=repo,
    )
    if pf.returncode:
        return 0 if a.advisory else 2
    checks = []
    selected = a.image or list(p["images"])
    for name in selected:
        spec = p["images"][name]
        dockerfile = repo / spec["dockerfile"]
        tag = f"omp-fadd-{name}:{int(time.time())}"
        checks.append(
            run(f"{name}-hadolint", ["hadolint", str(dockerfile)], repo, out)
        )
        build = [
            "docker",
            "buildx",
            "build",
            "--load",
            "--platform",
            spec.get("platform", "linux/amd64"),
            "-f",
            str(dockerfile),
            "-t",
            tag,
        ]
        if spec.get("target"):
            build.extend(["--target", spec["target"]])
        build.append(spec.get("context", "."))
        checks.append(run(f"{name}-build", build, repo, out))
        if checks[-1]["status"] != "pass":
            continue
        checks.append(
            run(
                f"{name}-size",
                [
                    "disl",
                    tag,
                    spec["maxSize"],
                    f"--max-layers={spec['maxLayers']}",
                    "--current-size",
                ],
                repo,
                out,
            )
        )
        checks.append(
            run(
                f"{name}-dive",
                [
                    "dive",
                    tag,
                    "--ci",
                    f"--lowestEfficiency={spec['minimumEfficiency']}",
                ],
                repo,
                out,
            )
        )
        checks.append(
            run(
                f"{name}-trivy",
                [
                    "trivy",
                    "image",
                    "--severity",
                    "HIGH,CRITICAL",
                    "--exit-code",
                    "1",
                    "--format",
                    "json",
                    "--output",
                    str(out / f"{name}-trivy.json"),
                    tag,
                ],
                repo,
                out,
            )
        )
        checks.append(
            run(
                f"{name}-sbom",
                [
                    "syft",
                    tag,
                    "-o",
                    f"cyclonedx-json={out / f'{name}-sbom.json'}",
                ],
                repo,
                out,
            )
        )
        smoke = spec.get("smoke", {}).get("command") or []
        if smoke:
            checks.append(
                run(
                    f"{name}-smoke",
                    ["docker", "run", "--rm", tag, *smoke],
                    repo,
                    out,
                    timeout=spec.get("smoke", {}).get("timeoutSeconds", 30),
                )
            )
        size = image_size(tag, repo)
        (out / f"{name}-metadata.json").write_text(
            json.dumps({"image": tag, "sizeBytes": size}, indent=2) + "\n"
        )
        subprocess.run(
            ["docker", "image", "rm", "-f", tag], cwd=repo, capture_output=True
        )
    status = (
        "blocked"
        if any(c["status"] == "blocked" for c in checks)
        else "fail"
        if any(c["status"] == "fail" for c in checks)
        else "pass"
    )
    result = {"schemaVersion": "1.0", "status": status, "checks": checks}
    (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return (
        0
        if status == "pass" or a.advisory
        else 2
        if status == "blocked"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
