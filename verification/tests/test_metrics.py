from __future__ import annotations

from types import MappingProxyType

import pytest

from sird_verification import metrics
from sird_verification.metrics import MetricStatus as Status
from sird_verification.metrics import MetricStratum as Stratum

META = MappingProxyType(
    {
        "corpus": "sird",
        "corpus_version": "2026-09",
        "variant": "baseline",
        "mode": "strict",
        "form": "invoice",
        "quality_stratum": Stratum.HIGH,
        "comparison_policy": "grouped-source-v1",
        "evaluator_version": "metrics-1",
    },
)

_TWO = 2.0
_THREE = 3.0
_FOUR = 4.0
_FIVE = 5
_TWENTY = 20
_THIRTY = 30
_FORTY = 40
_EIGHT = 8.0
_TEN = 10
_TWELVE_AND_HALF = 12.5
_NINETEEN_AND_QUARTER = 19.25
_NINETY_NINE = 99
_NINE_TENTHS = 0.9
_TWO_TENTHS = 0.2
_ONE_TENTH = 0.1
_ONE_THIRD = 1 / 3
_TWO_THIRDS = 2 / 3
_ZERO = 0


class TestMetricRates:
    def test_exact_accuracy_preserves_counts(self) -> None:
        metric_result = metrics.exact_field_accuracy(
            ["a", "b", "c"],
            ["a", "x", "c"],
            **META,
        )

        assert metric_result.status is Status.AVAILABLE
        assert (
            metric_result.numerator,
            metric_result.denominator,
            metric_result.value,
        ) == (
            _TWO,
            _THREE,
            pytest.approx(_TWO_THIRDS),
        )
        assert metric_result.corpus_version == "2026-09"
        assert metric_result.quality_stratum is Stratum.HIGH

    def test_rates_keep_zero_denominator_unavailable(self) -> None:
        for metric in (
            metrics.refusal_rate,
            metrics.false_output_rate,
            metrics.corruption_rate,
            metrics.form_accuracy,
        ):
            if metric is metrics.form_accuracy:
                metric_result = metric([], [], **META)
            else:
                metric_result = metric([], **META)
            assert metric_result.status is Status.UNAVAILABLE
            assert metric_result.value is None
            assert metric_result.denominator == _ZERO

    def test_grouped_observations_count_once(self) -> None:
        metric_result = metrics.refusal_rate([False, True, True], **META)

        assert metric_result.numerator == _TWO
        assert metric_result.denominator == _THREE
        assert metric_result.value == pytest.approx(_TWO_THIRDS)

    def test_cer_is_auxiliary_character_error_rate(self) -> None:
        metric_result = metrics.cer_auxiliary(["abc"], ["axc"], **META)

        assert metric_result.metric == "cer"
        assert metric_result.numerator == pytest.approx(1.0)
        assert metric_result.denominator == _THREE
        assert metric_result.value == pytest.approx(_ONE_THIRD)

    def test_cer_can_exceed_one(self) -> None:
        metric_result = metrics.cer_auxiliary(["a"], ["abcdef"], **META)

        assert metric_result.status is Status.AVAILABLE
        assert metric_result.value == _FIVE


class TestMetricResources:
    def test_latency_uses_nearest_rank_p99(self) -> None:
        metric_result = metrics.latency_percentile(
            [_THIRTY, _TEN, _TWENTY, _FORTY],
            percentile=_NINETY_NINE,
            **META,
        )

        assert metric_result.status is Status.AVAILABLE
        assert metric_result.value == _FORTY
        assert metric_result.denominator == _FOUR

    def test_memory_peak_reports_maximum(self) -> None:
        metric_result = metrics.memory_peak(
            [_TWELVE_AND_HALF, _EIGHT, _NINETEEN_AND_QUARTER],
            **META,
        )

        assert metric_result.status is Status.AVAILABLE
        assert metric_result.value == _NINETEEN_AND_QUARTER
        assert metric_result.numerator == _NINETEEN_AND_QUARTER

    def test_geometry_and_uncertainty_metrics(self) -> None:
        iou_box = (0, 0, 2, 2)
        overlap_box = (1, 0, 3, 2)
        iou = metrics.geometry_iou([iou_box], [overlap_box], **META)
        metric_result = metrics.uncertainty_brier(
            [_NINE_TENTHS, _TWO_TENTHS],
            [True, False],
            **META,
        )

        assert iou.value == pytest.approx(_ONE_THIRD)
        assert metric_result.value == pytest.approx(
            (_ONE_TENTH**2 + _TWO_TENTHS**2) / _TWO,
        )

    def test_invalid_measurements_blocked(self) -> None:
        latency = metrics.latency_percentile([_TEN, float("nan")], **META)
        invalid_box = (0, 0, 0, 1)
        valid_box = (0, 0, 1, 1)
        geometry = metrics.geometry_iou([invalid_box], [valid_box], **META)

        assert latency.status is Status.BLOCKED
        assert latency.value is None
        assert geometry.status is Status.BLOCKED
        assert geometry.value is None
