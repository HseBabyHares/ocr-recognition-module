"""Narrow validation helpers shared by persistence collaborators."""

from datetime import UTC, datetime

from sird_workflow.db import TaskRecord
from sird_workflow.invalid_task_event_error import InvalidTaskEventError
from sird_workflow.task_event import TaskEvent


def same_timestamp(left: datetime, right: datetime) -> bool:
    """Compare PostgreSQL and SQLite timestamp values in UTC."""
    left_utc = (
        left.replace(tzinfo=UTC)
        if left.tzinfo is None
        else left.astimezone(UTC)
    )
    right_utc = (
        right.replace(tzinfo=UTC)
        if right.tzinfo is None
        else right.astimezone(UTC)
    )
    return left_utc == right_utc


def _timestamps_match(task: TaskRecord, event: TaskEvent) -> bool:
    return same_timestamp(task.created_at, event.submitted_at) and (
        same_timestamp(
            task.retention_expires_at,
            event.retention_expires_at,
        )
    )


def _event_content_matches(task: TaskRecord, event: TaskEvent) -> bool:
    return (
        task.artifact_ref == event.artifact_ref
        and task.policy == dict(event.policy)
        and task.retention_seconds == event.retention_seconds
        and _timestamps_match(task, event)
    )


def validate_event_against_task(task: TaskRecord, event: TaskEvent) -> None:
    if task.request_id != event.request_id:
        raise InvalidTaskEventError("task request identity does not match")
    if not _event_content_matches(task, event):
        raise InvalidTaskEventError(
            "task event content does not match durable task state"
        )


def require_text(candidate: str, name: str) -> None:
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError(f"{name} must be a non-empty string")
