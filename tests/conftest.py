from __future__ import annotations

from collections.abc import Iterator

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from sird_recognition import telemetry
from tests._object_store import object_store


@pytest.fixture
def store() -> Iterator[str]:
    """Yield the endpoint of a local S3 stand-in."""
    with object_store() as endpoint:
        yield endpoint


@pytest.fixture
def metric_points(monkeypatch: pytest.MonkeyPatch) -> InMemoryMetricReader:
    """Route OCR latency histogram points to an in-memory reader."""
    reader = InMemoryMetricReader()
    meter = MeterProvider(metric_readers=[reader]).get_meter("test")
    monkeypatch.setattr(
        telemetry, "_duration", meter.create_histogram("duration")
    )
    return reader
