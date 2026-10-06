"""Fetch and verify the pinned local GLiNER model bundle during image build."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download

_MODEL_ID = "urchade/gliner_multi-v2.1"
_MODEL_REVISION = "443d26d654e0324125a96bebd8e796c14ff2efe6"
_TOKENIZER_ID = "microsoft/mdeberta-v3-base"
_TOKENIZER_REVISION = "a0484667b22365f84929a935b5e50a51f71f159d"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(stream.read, b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(repo: str, filename: str, revision: str) -> bytes:
    source = hf_hub_download(repo, filename, revision=revision)
    return Path(source).read_bytes()


def _load_checksums(path: Path) -> dict[Path, str]:
    checksums: dict[Path, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, target = line.split("  ", 1)
        checksums[Path(target)] = digest
    return checksums


def _write_download(
    repo: str,
    filename: str,
    revision: str,
    targets: tuple[Path, ...],
) -> None:
    downloaded_bytes = _download(repo, filename, revision)
    for target in targets:
        target.write_bytes(downloaded_bytes)


def fetch(model_dir: Path, backbone_dir: Path, checksums_path: Path) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    backbone_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "model.safetensors").write_bytes(
        _download(_MODEL_ID, "model.safetensors", _MODEL_REVISION)
    )
    (model_dir / "gliner_config.json").write_bytes(
        _download(_MODEL_ID, "gliner_config.json", _MODEL_REVISION)
    )
    for filename in ("config.json", "tokenizer_config.json", "spm.model"):
        _write_download(
            _TOKENIZER_ID,
            filename,
            _TOKENIZER_REVISION,
            (backbone_dir / filename, model_dir / filename),
        )
    snapshot_download(
        _TOKENIZER_ID,
        revision=_TOKENIZER_REVISION,
        local_dir=backbone_dir,
        allow_patterns=("config.json", "tokenizer_config.json", "spm.model"),
    )
    config_path = model_dir / "gliner_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["model_name"] = str(backbone_dir)
    config_path.write_text(json.dumps(config, separators=(",", ":")))

    for target, expected in _load_checksums(checksums_path).items():
        if _sha256(target) != expected:
            sys.exit(f"checksum mismatch: {target}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--backbone-dir", type=Path, required=True)
    parser.add_argument("--checksums", type=Path, required=True)
    args = parser.parse_args()
    fetch(args.model_dir, args.backbone_dir, args.checksums)


if __name__ == "__main__":
    main()
