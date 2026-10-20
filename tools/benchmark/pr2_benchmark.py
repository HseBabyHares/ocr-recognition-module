"""Frozen synthetic benchmark for SRS PR-2 accuracy and PR-4 latency.

The corpus is fixed by seeds and by a committed SHA-256 lock. The run uses
the production reader composition (Tesseract, no GLiNER). The scorer reads
only the saved predictions and the ground truth, and it writes aggregates.

Run from the repository root:
  uv run python tools/benchmark/pr2_benchmark.py freeze
  uv run python tools/benchmark/pr2_benchmark.py run
  uv run python tools/benchmark/pr2_benchmark.py score
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = Path(__file__).with_name("pr2-corpus.lock.json")
WORK = ROOT / "artifacts" / "benchmark" / "pr2"
REPORT = ROOT / "docs" / "acceptance" / "pr2-benchmark-report.json"
RENDERER = ROOT / "tools" / "corpus" / "render_snils_forms.py"

# Development samples use seeds 0 and 3; benchmark seeds must differ.
ACQUISITIONS = {"photo": (1250, False), "scan": (1260, True)}
COUNT_PER_LAYOUT = 20
FIELDS = ("snils_number", "full_name", "birth_date")
THRESHOLDS = {
    "field_accuracy_min": 0.90,
    "latency_p99_max_seconds": 10.0,
    "peak_rss_max_bytes": 4 * 1024**3,
}
TIMEOUT_SECONDS = 30.0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render(out: Path) -> dict[str, dict[str, str]]:
    hashes: dict[str, dict[str, str]] = {}
    for acquisition, (seed, clean) in ACQUISITIONS.items():
        target = out / acquisition
        command = ["uv", "run", "-q", str(RENDERER), "--out", str(target)]
        command += ["--count", str(COUNT_PER_LAYOUT), "--seed", str(seed)]
        subprocess.run(
            [*command, *(["--clean"] if clean else [])],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        hashes[acquisition] = {
            path.name: _sha256(path)
            for path in sorted(target.iterdir())
            if path.is_file()
        }
    return hashes


def _lock_body(hashes: dict[str, dict[str, str]]) -> dict:
    return {
        "seeds": {name: seed for name, (seed, _) in ACQUISITIONS.items()},
        "count_per_layout": COUNT_PER_LAYOUT,
        "thresholds": THRESHOLDS,
        "files": hashes,
    }


def freeze() -> int:
    LOCK.write_text(json.dumps(_lock_body(_render(WORK)), indent=2) + "\n")
    return 0


def run() -> int:
    if _lock_body(_render(WORK)) != json.loads(LOCK.read_text()):
        print("corpus drift: rendered files do not match the lock")
        return 2
    from sird_recognition._tesseract_pins import tesseract_checksums
    from sird_recognition.snils_recognition import SnilsRecognitionService
    from sird_recognition.tesseract_text_reader import TesseractTextReader

    tesseract_sha, tessdata_sha = tesseract_checksums()
    service = SnilsRecognitionService(
        TesseractTextReader(
            implementation_checksum=tesseract_sha,
            tessdata_checksum=tessdata_sha,
        )
    )
    with (WORK / "predictions.jsonl").open("w") as predictions:
        for acquisition in ACQUISITIONS:
            manifest = WORK / acquisition / "manifest.jsonl"
            for line in manifest.read_text().splitlines():
                file = json.loads(line)["file"]
                image = (WORK / acquisition / file).read_bytes()
                started = time.perf_counter()
                result = service.recognize_image(
                    image, timeout_seconds=TIMEOUT_SECONDS
                )
                row = {
                    "acquisition": acquisition,
                    "file": file,
                    "latency_seconds": time.perf_counter() - started,
                    "status": result.status.value,
                }
                row |= {field: getattr(result, field) for field in FIELDS}
                predictions.write(json.dumps(row, ensure_ascii=False) + "\n")
    environment = {
        "tesseract_sha256": tesseract_sha,
        "tessdata_sha256": tessdata_sha,
        # Linux ru_maxrss is KiB; children is the largest Tesseract process.
        "peak_rss_kib": {
            "self": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "children": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        },
    }
    (WORK / "environment.json").write_text(json.dumps(environment) + "\n")
    return 0


def canonical(field: str, value: str | None) -> str | None:
    """Canonicalize for scoring only; API output is never changed."""
    if value is None:
        return None
    if field == "snils_number":
        return "".join(char for char in value if char.isdigit())
    if field == "full_name":
        return " ".join(value.casefold().split())
    return value.strip()


def percentile(values: list[float], rank: float) -> float:
    """Nearest-rank percentile; infinity for an empty run."""
    if not values:
        return math.inf
    ordered = sorted(values)
    return ordered[max(0, math.ceil(rank * len(ordered)) - 1)]


def score(truth: list[dict], predictions: list[dict]) -> dict:
    """Score saved predictions against truth; aggregates only.

    A refused, missing or wrong value is an error for that field.
    """
    by_key = {(row["acquisition"], row["file"]): row for row in predictions}
    counts: dict[str, dict[str, list[int]]] = {}
    for expected in truth:
        key = (expected["acquisition"], expected["file"])
        got = by_key.get(key, {})
        verified = got.get("status") == "verified"
        wanted = {**expected, "snils_number": expected["snils"]}
        for stratum in ("all", key[0], expected["layout"]):
            stratum_counts = counts.setdefault(stratum, {})
            for field in FIELDS:
                hit = verified and canonical(field, got.get(field)) == (
                    canonical(field, wanted[field])
                )
                pair = stratum_counts.setdefault(field, [0, 0])
                pair[0] += int(hit)
                pair[1] += 1
    accuracy = {
        stratum: {field: hits / total for field, (hits, total) in c.items()}
        for stratum, c in counts.items()
    }
    latencies = [row["latency_seconds"] for row in predictions]
    latency = {
        name: percentile(latencies, rank)
        for name, rank in (("p50", 0.50), ("p95", 0.95), ("p99", 0.99))
    }
    return {
        "documents": len(truth),
        "predictions": len(predictions),
        "verified": sum(row["status"] == "verified" for row in predictions),
        "accuracy": accuracy,
        "latency_seconds": latency,
        "accuracy_passed": bool(truth)
        and min(accuracy["all"].values()) >= THRESHOLDS["field_accuracy_min"],
        "latency_passed": latency["p99"]
        <= THRESHOLDS["latency_p99_max_seconds"],
    }


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def score_command() -> int:
    truth = [
        {**row, "acquisition": acquisition}
        for acquisition in ACQUISITIONS
        for row in _jsonl(WORK / acquisition / "manifest.jsonl")
    ]
    predictions = _jsonl(WORK / "predictions.jsonl")
    report = score(truth, predictions)
    # Latency varies per run; equal hashes prove reproducible predictions.
    stable = [
        {key: value for key, value in row.items() if key != "latency_seconds"}
        for row in predictions
    ]
    report["prediction_sha256"] = hashlib.sha256(
        json.dumps(stable, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    environment = json.loads((WORK / "environment.json").read_text())
    peak_bytes = max(environment.pop("peak_rss_kib").values()) * 1024
    report |= {
        "peak_rss_bytes": peak_bytes,
        "memory_passed": peak_bytes <= THRESHOLDS["peak_rss_max_bytes"],
        "lock_sha256": _sha256(LOCK),
        "thresholds": THRESHOLDS,
        "environment": {**environment, "platform": sys.platform},
    }
    report["passed"] = all(
        report[gate]
        for gate in ("accuracy_passed", "latency_passed", "memory_passed")
    )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"passed": report["passed"], **report["accuracy"]}))
    return 0 if report["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SRS PR-2 frozen OCR benchmark"
    )
    parser.add_argument("command", choices=("freeze", "run", "score"))
    commands = {"freeze": freeze, "run": run, "score": score_command}
    return commands[parser.parse_args().command]()


if __name__ == "__main__":
    raise SystemExit(main())
