#!/usr/bin/env python3
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[3]

with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td)
    bin_dir = td / "bin"
    repo = td / "repo"
    out = td / "out"
    bin_dir.mkdir()
    repo.mkdir()
    lock = json.loads(
        (ROOT / "tools/security/toolchain.lock.json").read_text()
    )["tools"]
    for name, spec in lock.items():
        script = bin_dir / spec["command"]
        script.write_text(
            "#!/bin/sh\n"
            'if [ "$1" = "--version" ] || [ "$1" = "version" ]; then echo "'
            + spec["version"]
            + '"; exit 0; fi\n'
            'case "$0" in\n'
            '  *trivy*) while [ $# -gt 0 ]; do if [ "$1" = "--output" ]; then shift; echo "{}" > "$1"; fi; shift; done;;\n'
            '  *semgrep*) while [ $# -gt 0 ]; do if [ "$1" = "--output" ]; then shift; echo "{}" > "$1"; fi; shift; done;;\n'
            '  *osv-scanner*) while [ $# -gt 0 ]; do if [ "$1" = "--output-file" ]; then shift; echo "{}" > "$1"; fi; shift; done;;\n'
            '  *gitleaks*) while [ $# -gt 0 ]; do if [ "$1" = "--report-path" ]; then shift; echo "[]" > "$1"; fi; shift; done;;\n'
            "esac\nexit 0\n"
        )
        script.chmod(0o755)
    env = {
        **os.environ,
        "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", ""),
    }
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/security/preflight.py"),
            "--strict",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/security/scan.py"),
            "--repo",
            str(repo),
            "--out",
            str(out),
            "--semgrep-config",
            str(ROOT / "tools/security/semgrep-policy.yml"),
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["status"] == "pass"
    assert all(not item["missingMachineReport"] for item in summary["scans"])
    assert (out / "osv-scanner.json").exists()

    # A scanner that exits zero without a machine report is BLOCKED, not clean.
    (bin_dir / "osv-scanner").write_text(
        '#!/bin/sh\nif [ "$1" = "--version" ]; then echo "'
        + lock["osv-scanner"]["version"]
        + '"; exit 0; fi\nexit 0\n'
    )
    (bin_dir / "osv-scanner").chmod(0o755)
    blocked_out = td / "blocked"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/security/scan.py"),
            "--repo",
            str(repo),
            "--out",
            str(blocked_out),
            "--semgrep-config",
            str(ROOT / "tools/security/semgrep-policy.yml"),
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert (
        json.loads((blocked_out / "summary.json").read_text())["status"]
        == "blocked"
    )

    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/security/install.py"), "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)

# request_json retries a 403 without the token (owner IP allow list).
sys.path.insert(0, str(ROOT / "tools/security"))
import install  # noqa: E402

sent = []


def fake_urlopen(req, timeout):
    sent.append(req.get_header("Authorization"))
    if req.get_header("Authorization"):
        raise urllib.error.HTTPError(
            req.full_url, 403, "Forbidden", {}, io.BytesIO(b"{}")
        )
    return io.BytesIO(b'{"ok": 1}')


os.environ["GITHUB_TOKEN"] = "self-test"
install.urllib.request.urlopen = fake_urlopen
assert install.request_json("https://api.github.com/x") == {"ok": 1}
assert sent == ["Bearer self-test", None], sent

print('{"check":"security-harness","status":"pass"}')
