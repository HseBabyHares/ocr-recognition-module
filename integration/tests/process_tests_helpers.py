from __future__ import annotations

from typing import Any


def assert_outbox_retry_report(report: Any) -> None:
    assert (
        report.result_attempted,
        report.result_published,
        report.result_failed,
        report.dead_letter_attempted,
        report.dead_letter_acknowledged,
        report.dead_letter_failed,
    ) == (1, 0, 1, 1, 0, 1)


def assert_outbox_retry_state(result_record: Any, dead_letter: Any) -> None:
    assert result_record is not None and result_record.published_at is None
    assert dead_letter is not None and dead_letter.acknowledged_at is None


def assert_outbox_success_report(report: Any) -> None:
    assert (
        report.result_attempted,
        report.result_published,
        report.result_failed,
        report.dead_letter_attempted,
        report.dead_letter_acknowledged,
        report.dead_letter_failed,
    ) == (1, 1, 0, 1, 1, 0)


def assert_outbox_success_state(result_record: Any, dead_letter: Any) -> None:
    assert result_record is not None and result_record.published_at is not None
    assert dead_letter is not None and dead_letter.acknowledged_at is not None


def assert_task_outbox_reports(first: Any, second: Any) -> None:
    assert (
        first.attempted,
        first.published,
        first.failed,
        second.attempted,
        second.published,
        second.failed,
    ) == (1, 0, 1, 1, 1, 0)
