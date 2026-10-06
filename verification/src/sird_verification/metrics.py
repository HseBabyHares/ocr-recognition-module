"""Versioned, explicit metric primitives for verification evidence."""

from __future__ import annotations

from sird_verification import _metric_accuracy as _accuracy
from sird_verification import _metric_geometry as _geometry
from sird_verification import _metric_models as _models
from sird_verification import _metric_runtime as _runtime
from sird_verification import _metric_text as _text
from sird_verification import _metric_uncertainty as _uncertainty

MetricRecord = _models.MetricRecord
MetricStatus = _models.MetricStatus
MetricStratum = _models.MetricStratum
cer_auxiliary = _text.cer_auxiliary
corruption_rate = _accuracy.corruption_rate
exact_field_accuracy = _accuracy.exact_field_accuracy
false_output_rate = _accuracy.false_output_rate
form_accuracy = _accuracy.form_accuracy
geometry_iou = _geometry.geometry_iou
latency_percentile = _runtime.latency_percentile
memory_peak = _runtime.memory_peak
refusal_rate = _accuracy.refusal_rate
uncertainty_brier = _uncertainty.uncertainty_brier
