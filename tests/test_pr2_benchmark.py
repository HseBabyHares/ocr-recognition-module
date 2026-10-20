import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).parents[1] / "tools" / "benchmark" / "pr2_benchmark.py"
)
_FIRST = "a.png"
_SPEC = spec_from_file_location("pr2_benchmark", _SCRIPT)
assert _SPEC and _SPEC.loader
benchmark = module_from_spec(_SPEC)
sys.modules[_SPEC.name] = benchmark
_SPEC.loader.exec_module(benchmark)


def _truth(name: str) -> dict[str, str]:
    return {
        "file": name,
        "layout": "snils_card",
        "acquisition": "scan",
        "snils": "11223344595",
        "full_name": "Иванов Иван Иванович",
        "birth_date": "1990-01-31",
    }


def _prediction(name: str = _FIRST, **changes: object) -> dict[str, object]:
    row = {
        "acquisition": "scan",
        "file": name,
        "latency_seconds": 1,
        "status": "verified",
        "snils_number": "112-233-445 95",
        "full_name": "ИВАНОВ  ИВАН ИВАНОВИЧ",
        "birth_date": "1990-01-31",
    }
    return row | changes


def test_canonical_match_counts_as_hit() -> None:
    report = benchmark.score([_truth(_FIRST)], [_prediction()])
    assert report["accuracy"]["all"] == dict.fromkeys(benchmark.FIELDS, 1)
    assert report["accuracy_passed"]
    assert report["latency_passed"]


def test_refused_wrong_missing_are_errors() -> None:
    truth = [_truth(_FIRST), _truth("b.png"), _truth("c.png")]
    predictions = [
        _prediction(status="refused"),
        _prediction("b.png", birth_date="1990-01-30"),
    ]
    report = benchmark.score(truth, predictions)
    assert report["accuracy"]["scan"]["birth_date"] == 0
    assert report["accuracy"]["snils_card"]["snils_number"] == pytest.approx(
        1 / 3
    )
    assert not report["accuracy_passed"]


def test_latency_gate_uses_nearest_rank_p99() -> None:
    limit = benchmark.THRESHOLDS["latency_p99_max_seconds"]
    slow = [_prediction(latency_seconds=limit + 1)]
    assert not benchmark.score([_truth(_FIRST)], slow)["latency_passed"]
    assert benchmark.percentile([1, 2, 3, 4], 0.5) == 2
