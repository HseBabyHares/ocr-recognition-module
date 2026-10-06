#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import venv
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "tools/security/toolchain.lock.json"


def load():
    return json.loads(LOCK.read_text())["tools"]


def request_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "omp-fadd-security-installer/1",
        },
    )
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def download(url, dst):
    req = urllib.request.Request(
        url, headers={"User-Agent": "omp-fadd-security-installer/1"}
    )
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and "github" in url:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=180) as r, dst.open("wb") as f:
        shutil.copyfileobj(r, f)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def target_tokens():
    osname = platform.system().lower()
    machine = platform.machine().lower()
    if osname not in {"linux", "darwin"}:
        raise RuntimeError(f"unsupported OS: {osname}")
    arch = (
        "amd64"
        if machine in {"x86_64", "amd64"}
        else "arm64"
        if machine in {"arm64", "aarch64"}
        else None
    )
    if not arch:
        raise RuntimeError(f"unsupported architecture: {machine}")
    return osname, arch


def score(name, tool, version, osname, arch):
    x = name.lower()
    if any(
        k in x
        for k in [
            "checksum",
            "sha256",
            "sbom",
            ".sig",
            "attestation",
            ".deb",
            ".rpm",
        ]
    ):
        return -999
    if osname == "linux" and "linux" not in x:
        return -999
    if osname == "darwin" and not any(
        k in x for k in ["darwin", "macos", "osx"]
    ):
        return -999
    if arch == "amd64" and any(
        k in x for k in ["32bit", "arm64", "aarch64", "ppc64", "s390x"]
    ):
        return -999
    archs = (
        ["amd64", "x86_64", "x64", "64bit"]
        if arch == "amd64"
        else ["arm64", "aarch64"]
    )
    if not any(k in x for k in archs):
        return -999
    value = (
        10
        if tool.replace("-", "") in x.replace("-", "").replace("_", "")
        else 0
    )
    value += 6 if version in x else 0
    value += 4 if x.endswith((".tar.gz", ".tgz", ".zip")) else 0
    return value


def choose_asset(release, tool, version):
    osname, arch = target_tokens()
    ranked = sorted(
        (
            (score(a["name"], tool, version, osname, arch), a)
            for a in release.get("assets", [])
        ),
        key=lambda x: x[0],
        reverse=True,
    )
    if not ranked or ranked[0][0] < 10:
        raise RuntimeError(
            f"no unambiguous release asset for {tool} {osname}/{arch}"
        )
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
        raise RuntimeError(
            f"ambiguous assets for {tool}: {ranked[0][1]['name']}, {ranked[1][1]['name']}"
        )
    return ranked[0][1]


def expected_digest(release, asset, tmp):
    digest = asset.get("digest")
    if isinstance(digest, str) and digest.startswith("sha256:"):
        return digest.split(":", 1)[1].lower()
    for item in release.get("assets", []):
        if not re.search(
            r"(?:checksums?|sha256)", item.get("name", ""), re.I
        ) or item["name"].endswith((".sig", ".json")):
            continue
        p = tmp / item["name"]
        download(item["browser_download_url"], p)
        for line in p.read_text(errors="replace").splitlines():
            m = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+?)\s*$", line)
            if m and Path(m.group(2)).name == asset["name"]:
                return m.group(1).lower()
    raise RuntimeError(
        f"publisher did not provide a verifiable SHA-256 for {asset['name']}"
    )


def extract(archive, binary, dst):
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        if archive.name.endswith((".tar.gz", ".tgz")):
            with tarfile.open(archive, "r:gz") as tf:
                tf.extractall(out, filter="data")
        elif archive.name.endswith(".zip"):
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(out)
        else:
            shutil.copy2(archive, dst)
            dst.chmod(
                dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )
            return
        c = [
            p
            for p in out.rglob("*")
            if p.is_file()
            and p.name.lower() in {binary.lower(), f"{binary}.exe".lower()}
        ]
        if len(c) != 1:
            raise RuntimeError(
                f"expected one {binary} executable in {archive.name}; found {len(c)}"
            )
        shutil.copy2(c[0], dst)
        dst.chmod(
            dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )


def install_binary(name, spec, prefix, dry):
    api = f"https://api.github.com/repos/{spec['repository']}/releases/tags/{spec['tag']}"
    if dry:
        return {
            "tool": name,
            "version": spec["version"],
            "status": "planned",
            "source": api,
        }
    release = request_json(api)
    asset = choose_asset(release, name, spec["version"])
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        archive = td / asset["name"]
        download(asset["browser_download_url"], archive)
        expected = expected_digest(release, asset, td)
        observed = sha(archive)
        if expected != observed:
            raise RuntimeError(f"checksum mismatch for {asset['name']}")
        dst = prefix / "bin" / name
        extract(archive, name, dst)
    return {
        "tool": name,
        "version": spec["version"],
        "status": "installed",
        "asset": asset["name"],
        "sha256": observed,
    }


def install_python(name, spec, prefix, dry):
    if dry:
        return {
            "tool": name,
            "version": spec["version"],
            "status": "planned",
            "source": "PyPI isolated venv",
        }
    env_parent = prefix / "venvs"
    dst = prefix / "bin" / name
    old_env = None
    if dst.is_symlink():
        candidate = dst.resolve(strict=False).parent.parent
        if candidate.parent == env_parent and candidate.name.startswith(
            f"{name}-"
        ):
            old_env = candidate
    staged = Path(
        tempfile.mkdtemp(prefix=f"{name}-{spec['version']}-", dir=env_parent)
    )
    staged_link = None
    installed = False
    try:
        venv.EnvBuilder(with_pip=True).create(staged)
        python = staged / "bin" / "python"
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                f"{spec['package']}=={spec['version']}",
            ],
            check=True,
        )
        with tempfile.NamedTemporaryFile(
            dir=prefix / "bin", prefix=f".{name}.", delete=False
        ) as handle:
            staged_link = Path(handle.name)
        staged_link.unlink()
        staged_link.symlink_to(staged / "bin" / name)
        os.replace(staged_link, dst)
        staged_link = None
        installed = True
        if old_env is not None and old_env != staged:
            shutil.rmtree(old_env, ignore_errors=True)
    except Exception:
        if staged_link is not None:
            staged_link.unlink(missing_ok=True)
        raise
    finally:
        if not installed:
            shutil.rmtree(staged, ignore_errors=True)
    return {
        "tool": name,
        "version": spec["version"],
        "status": "installed",
        "source": "PyPI isolated venv",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--prefix", type=Path, default=Path.home() / ".local/omp-fadd/security"
    )
    ap.add_argument("--tool", action="append")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    specs = load()
    names = a.tool or list(specs)
    unknown = set(names) - set(specs)
    if unknown:
        raise SystemExit(f"unknown tools: {sorted(unknown)}")
    prefix = a.prefix.expanduser().resolve()
    if not a.dry_run:
        (prefix / "bin").mkdir(parents=True, exist_ok=True)
        (prefix / "venvs").mkdir(parents=True, exist_ok=True)
    records = []
    try:
        for name in names:
            spec = specs[name]
            records.append(
                install_python(name, spec, prefix, a.dry_run)
                if spec["install"] == "python-venv"
                else install_binary(name, spec, prefix, a.dry_run)
            )
        result = {
            "schemaVersion": "1.0",
            "status": "planned" if a.dry_run else "installed",
            "prefix": str(prefix),
            "records": records,
        }
        if not a.dry_run:
            (prefix / "install-manifest.json").write_text(
                json.dumps(result, indent=2) + "\n"
            )
        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(
            json.dumps(
                {"schemaVersion": "1.0", "status": "blocked", "error": str(e)},
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
