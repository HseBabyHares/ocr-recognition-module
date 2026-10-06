#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def run_scan(
    name: str,
    command: list[str],
    report: Path,
    log: Path,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> dict:
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    result = subprocess.run(
        command, cwd=cwd, capture_output=True, text=True, env=env
    )
    log.write_text(
        (result.stdout or "") + (result.stderr or ""), encoding="utf-8"
    )

    missing_machine_report = not report.exists() or report.stat().st_size == 0
    if (
        missing_machine_report
        and name.startswith("gitleaks")
        and result.returncode == 0
    ):
        report.write_text("[]\n", encoding="utf-8")
        missing_machine_report = False
    elif missing_machine_report:
        report.write_text(
            json.dumps(
                {
                    "scanner": name,
                    "status": "missing-machine-report",
                    "exitCode": result.returncode,
                }
            )
            + "\n",
            encoding="utf-8",
        )

    parse_ok = True
    try:
        json.loads(report.read_text(encoding="utf-8"))
    except Exception:
        parse_ok = False

    if (
        missing_machine_report
        or not parse_ok
        or result.returncode not in (0, 1)
    ):
        status = "blocked"
    elif result.returncode == 1:
        status = "findings"
    else:
        status = "pass"

    return {
        "scanner": name,
        "status": status,
        "exitCode": result.returncode,
        "command": command,
        "report": str(report),
        "reportSha256": digest(report),
        "log": str(log),
        "missingMachineReport": missing_machine_report,
        "parseOk": parse_ok,
        "startedAt": started,
        "finishedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def default_cache() -> Path:
    configured = os.environ.get("SECURITY_CACHE_DIR")
    if configured:
        return Path(configured).expanduser()
    cache_home = os.environ.get("XDG_CACHE_HOME")
    root = (
        Path(cache_home).expanduser() if cache_home else Path.home() / ".cache"
    )
    return root / "omp-fadd" / "security"


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path("security-reports"))
    parser.add_argument("--cache", type=Path, default=default_cache())
    parser.add_argument(
        "--semgrep-config", default="tools/security/semgrep-policy.yml"
    )
    args = parser.parse_args()

    repo = args.repo.resolve()
    out = args.out.resolve()
    cache = args.cache.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if path_is_within(cache, repo):
        result = {
            "schemaVersion": "1.1",
            "status": "blocked",
            "reason": "scanner-cache-inside-repository",
            "cache": str(cache),
            "repository": str(repo),
            "scans": [],
        }
        text = json.dumps(result, indent=2) + "\n"
        (out / "summary.json").write_text(text, encoding="utf-8")
        print(text, end="")
        return 2

    preflight = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/security/preflight.py"),
            "--strict",
            "--out",
            str(out / "preflight.json"),
        ],
        cwd=repo,
    )
    if preflight.returncode:
        result = {
            "schemaVersion": "1.1",
            "status": "blocked",
            "reason": "scanner-preflight",
            "scans": [],
        }
        (out / "summary.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, indent=2))
        return 2

    scans: list[dict] = []
    trivy = [
        "trivy",
        "--cache-dir",
        str(cache / "trivy"),
        "fs",
        "--scanners",
        "vuln,misconfig,secret",
        "--severity",
        "HIGH,CRITICAL",
        "--exit-code",
        "1",
        "--format",
        "json",
        "--output",
        str(out / "trivy.json"),
        ".",
    ]
    if (cache / "trivy" / "db" / "metadata.json").exists():
        trivy.insert(4, "--skip-db-update")
    scans.append(
        run_scan("trivy", trivy, out / "trivy.json", out / "trivy.log", repo)
    )

    semgrep = [
        "semgrep",
        "scan",
        "--config",
        args.semgrep_config,
        "--jobs",
        "1",
        "--error",
        "--json",
        "--output",
        str(out / "semgrep.json"),
        ".",
    ]
    scans.append(
        run_scan(
            "semgrep",
            semgrep,
            out / "semgrep.json",
            out / "semgrep.log",
            repo,
            {**os.environ, "EIO_BACKEND": "posix"},
        )
    )

    osv_report = out / "osv-scanner.json"
    osv = ["osv-scanner"]
    if (cache / "metadata.json").exists() or any((cache / "osv").glob("*")):
        osv.append("--offline-vulnerabilities")
    osv.extend(
        [
            "scan",
            "source",
            "-r",
            "--format",
            "json",
            "--output-file",
            str(osv_report),
            ".",
        ]
    )
    scans.append(
        run_scan(
            "osv-scanner",
            osv,
            osv_report,
            out / "osv-scanner.log",
            repo,
            {
                **os.environ,
                "OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY": str(cache / "osv"),
            },
        )
    )

    for mode in ("git", "dir"):
        report = out / f"gitleaks-{mode}.json"
        command = [
            "gitleaks",
            mode,
            "--redact",
            "--no-banner",
            "--exit-code",
            "1",
            "--report-format",
            "json",
            "--report-path",
            str(report),
            ".",
        ]
        scans.append(
            run_scan(
                f"gitleaks-{mode}",
                command,
                report,
                out / f"gitleaks-{mode}.log",
                repo,
            )
        )

    status = (
        "blocked"
        if any(item["status"] == "blocked" for item in scans)
        else "fail"
        if any(item["status"] == "findings" for item in scans)
        else "pass"
    )
    result = {
        "schemaVersion": "1.1",
        "status": status,
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scans": scans,
    }
    (out / "summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return {"pass": 0, "fail": 1, "blocked": 2}[status]


if __name__ == "__main__":
    raise SystemExit(main())
