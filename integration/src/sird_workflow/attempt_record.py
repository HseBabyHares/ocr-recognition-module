"""Conversion helpers for persisted attempt budget records."""

from datetime import UTC, datetime

from sird_workflow.attempts import AttemptBudget, AttemptLease
from sird_workflow.backoff import backoff_seconds
from sird_workflow.db import TaskAttemptRecord


def bounded_retry_delay(
    next_attempt_at: datetime, now: datetime, attempts_used: int
) -> float:
    scheduled_utc = (
        next_attempt_at.replace(tzinfo=UTC)
        if next_attempt_at.tzinfo is None
        else next_attempt_at.astimezone(UTC)
    )
    now_utc = now.astimezone(UTC)
    remaining = max(0, (scheduled_utc - now_utc).total_seconds())
    if remaining == 0 or attempts_used <= 0:
        return remaining
    return min(remaining, backoff_seconds(attempts_used))


def lease_from_record(
    record: TaskAttemptRecord, worker_id: str
) -> AttemptLease:
    delivery_id = record.active_delivery_id or f"{record.task_id}:exhausted"
    lease_id = record.active_lease_id or f"{record.task_id}:{delivery_id}"
    return AttemptLease(
        task_id=record.task_id,
        attempt_number=max(record.attempts_used, 1),
        fencing_token=max(record.fencing_token, 1),
        worker_id=record.active_worker_id or worker_id,
        lease_id=lease_id,
        delivery_id=delivery_id,
    )


def budget_from_record(
    record: TaskAttemptRecord, worker_id: str
) -> AttemptBudget:
    active_lease = None
    if (
        record.active_delivery_id is not None
        and record.active_lease_id is not None
    ):
        active_lease = lease_from_record(record, worker_id)
    return AttemptBudget(
        task_id=record.task_id,
        max_attempts=record.max_attempts,
        attempts_used=record.attempts_used,
        fencing_token=record.fencing_token,
        active_lease=active_lease,
        terminal_outcome=record.terminal_outcome,
        terminal_result_id=record.terminal_result_id,
    )
