#!/usr/bin/env python3
# Reuse the verified GitHub release installer implementation used for container binaries.
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import platform
import re
import shutil
import stat
import tarfile
import tempfile
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOCK = json.loads((ROOT / "tools/meta/toolchain.lock.json").read_text())[
    "tools"
]


def api(url):
    return json.load(
        urllib.request.urlopen(
            urllib.request.Request(
                url, headers={"User-Agent": "omp-fadd-meta"}
            ),
            timeout=60,
        )
    )


def get(url, p):
    shutil.copyfileobj(
        urllib.request.urlopen(
            urllib.request.Request(
                url, headers={"User-Agent": "omp-fadd-meta"}
            ),
            timeout=180,
        ),
        p.open("wb"),
    )


def score(n, tool):
    n = n.lower()
    sysn = platform.system().lower()
    arch = platform.machine().lower()
    archs = (
        ["x86_64", "amd64", "64bit"]
        if arch in {"x86_64", "amd64"}
        else ["arm64", "aarch64"]
    )
    if sysn == "linux" and "linux" not in n:
        return -999
    if sysn == "darwin" and not any(x in n for x in ["darwin", "macos"]):
        return -999
    if not any(x in n for x in archs):
        return -999
    if any(x in n for x in ["checksum", "sha256", ".sig"]):
        return -999
    return (10 if tool in n else 0) + (
        3 if n.endswith((".tar.gz", ".tgz", ".zip")) else 0
    )


def digest(a, rel, tmp):
    d = a.get("digest")
    if isinstance(d, str) and d.startswith("sha256:"):
        return d.split(":", 1)[1]
    for c in rel["assets"]:
        if re.search(r"checksums?|sha256", c["name"], re.I) and not c[
            "name"
        ].endswith(".sig"):
            p = tmp / c["name"]
            get(c["browser_download_url"], p)
            for line in p.read_text(errors="ignore").splitlines():
                m = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+)$", line)
                if m and pathlib.Path(m.group(2)).name == a["name"]:
                    return m.group(1).lower()
    raise RuntimeError(f"no digest for {a['name']}")


def install(tool, prefix, dry):
    m = LOCK[tool]
    if dry:
        return {
            "tool": tool,
            "version": m["version"],
            "status": "planned",
            "source": m.get("repository") or m.get("package"),
        }
    if m.get("install") == "python-venv":
        import subprocess
        import venv

        env = prefix / "venvs" / f"{tool}-{m['version']}"
        venv.EnvBuilder(with_pip=True, clear=True).create(env)
        subprocess.run(
            [
                str(env / "bin" / "python"),
                "-m",
                "pip",
                "install",
                f"{m['package']}=={m['version']}",
            ],
            check=True,
        )
        d = prefix / "bin" / tool
        d.parent.mkdir(parents=True, exist_ok=True)
        d.unlink(missing_ok=True)
        d.symlink_to(env / "bin" / tool)
        return {"tool": tool, "status": "installed", "version": m["version"]}
    rel = api(
        f"https://api.github.com/repos/{m['repository']}/releases/tags/v{m['version']}"
    )
    rank = sorted(
        ((score(a["name"], tool), a) for a in rel["assets"]),
        key=lambda x: x[0],
        reverse=True,
    )
    a = rank[0][1]
    if rank[0][0] < 3:
        raise RuntimeError(f"no asset {tool}")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        arc = tmp / a["name"]
        get(a["browser_download_url"], arc)
        obs = hashlib.sha256(arc.read_bytes()).hexdigest()
        exp = digest(a, rel, tmp)
        if obs != exp:
            raise RuntimeError("digest mismatch")
        x = tmp / "x"
        x.mkdir()
        if arc.name.endswith((".tar.gz", ".tgz")):
            with tarfile.open(arc, "r:gz") as tf:
                tf.extractall(x, filter="data")
        elif arc.name.endswith(".zip"):
            with zipfile.ZipFile(arc) as z:
                z.extractall(x)
        cand = [
            p
            for p in x.rglob("*")
            if p.is_file() and p.name.lower() in {tool, f"{tool}.exe"}
        ]
        if len(cand) != 1:
            raise RuntimeError(f"ambiguous {tool}")
        d = prefix / "bin" / tool
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cand[0], d)
        d.chmod(d.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return {"tool": tool, "status": "installed", "sha256": obs}


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--prefix",
        type=pathlib.Path,
        default=pathlib.Path.home() / ".local/omp-meta",
    )
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    print(
        json.dumps(
            {
                "records": [
                    install(t, a.prefix.expanduser().resolve(), a.dry_run)
                    for t in LOCK
                ]
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
