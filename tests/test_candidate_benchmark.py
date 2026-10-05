from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

SAMPLE_COUNT: Final = 30
WARMUP_ITERATIONS: Final = 5
MIN_SAMPLE_COUNT: Final = 10
P99_BOUNDARY: Final = (
    "p99 <= 10s and peak RSS <= 4GiB on representative CPU corpus"
)


class BenchmarkStatus(StrEnum):
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class CandidateBenchmarkEvidence:
    """Predeclared benchmark contract; no model is loaded by this test."""

    status: BenchmarkStatus
    warmup_iterations: int
    sample_count: int
    memory_scope: str
    latency_aggregation: str
    acceptance_boundary: str
    reason: str


def _benchmark_evidence() -> CandidateBenchmarkEvidence:
    return CandidateBenchmarkEvidence(
        status=BenchmarkStatus.BLOCKED,
        warmup_iterations=WARMUP_ITERATIONS,
        sample_count=SAMPLE_COUNT,
        memory_scope="process peak RSS including model and tokenizer",
        latency_aggregation="nearest-rank p99 over post-warmup samples",
        acceptance_boundary=P99_BOUNDARY,
        reason=(
            "blocked: representative OCR corpus and acceptance-run model are "
            "not available in this checkout"
        ),
    )


def test_benchmark_boundary_blocked() -> None:
    evidence = _benchmark_evidence()
    assert (
        evidence.status is BenchmarkStatus.BLOCKED,
        evidence.sample_count >= MIN_SAMPLE_COUNT,
        bool(evidence.memory_scope),
        "p99" in evidence.latency_aggregation,
        bool(evidence.acceptance_boundary),
        "representative" in evidence.reason,
    ) == (True, True, True, True, True, True)
