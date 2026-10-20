"""OCR latency metrics for SRS PR-4, exported through OTLP.

The histogram carries only low-cardinality status attributes. It never
records field values, document bytes, object keys, tokens or request ids.
"""

from __future__ import annotations

import os

from opentelemetry import metrics

from sird_recognition._runtime_models import RecognitionResponse

# Seconds; dense below 10 s so p50/p95/p99 of OCR calls stay resolvable.
_BUCKETS = (
    0.1,
    0.25,
    0.5,
    1,
    1.5,
    2,
    3,
    4,
    5,
    7.5,
    10,
    15,
    20,
    30,
    60,
)
_ENDPOINTS = (
    "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
)

_duration = metrics.get_meter("sird_recognition").create_histogram(
    "sird.ocr.recognition.duration",
    unit="s",
    description="Wall time of one Recognize call inside the OCR service.",
    explicit_bucket_boundaries_advisory=_BUCKETS,
)


def record_recognition(
    seconds: float, response: RecognitionResponse | None
) -> None:
    """Record one call; a None response is an internal runtime failure."""
    if response is None:
        attributes = {"sird.ocr.operation_status": "internal_error"}
    else:
        outcome = response.task_outcome
        attributes = {
            "sird.ocr.operation_status": str(response.operation_status),
            "sird.ocr.task_outcome": str(outcome) if outcome else "none",
        }
    _duration.record(seconds, attributes)


def configure_metrics() -> None:
    """Export metrics over OTLP/HTTP when a standard endpoint is set."""
    if not any(os.environ.get(name) for name in _ENDPOINTS):
        return
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import (
        PeriodicExportingMetricReader,
    )
    from opentelemetry.sdk.resources import Resource

    metrics.set_meter_provider(
        MeterProvider(
            metric_readers=[
                PeriodicExportingMetricReader(OTLPMetricExporter())
            ],
            resource=Resource.create({"service.name": "sird-ocr-server"}),
        )
    )
