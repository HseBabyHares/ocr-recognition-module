"""Stable enum values used by experiment contracts."""

from enum import StrEnum

_MODEL_MODULE = "sird_experiment.models"


class ExperimentMode(StrEnum):
    __module__ = _MODEL_MODULE
    END_TO_END = "end_to_end"
    REPLAY_METRICS = "replay_metrics"


class ExperimentStatus(StrEnum):
    __module__ = _MODEL_MODULE
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"
    RUNNING = "running"
    COMPLETE = "complete"


class SampleStatus(StrEnum):
    __module__ = _MODEL_MODULE
    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"
    LIMIT_EXCEEDED = "limit_exceeded"
    NOT_RUN = "not_run"
