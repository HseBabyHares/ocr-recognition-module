"""Explicit configuration for the trusted SIRD workflow boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from sird_workflow.models import DEFAULT_RETENTION_SECONDS
from sird_workflow.mtls import TlsClientIdentity


def _validate_routes(config: WorkflowConfig) -> None:
    for name in (
        "rabbitmq_exchange",
        "rabbitmq_task_route",
        "rabbitmq_result_route",
        "rabbitmq_retry_route",
        "rabbitmq_terminal_route",
    ):
        if not getattr(config, name):
            raise ValueError(f"{name} must not be empty")


def _validate_limits(config: WorkflowConfig) -> None:
    _require_positive(
        config.default_retention_seconds,
        "default_retention_seconds",
    )
    _require_positive(config.max_attempts, "max_attempts")
    _require_prefetch(config.rabbitmq_prefetch_count)
    _require_authorized_callers(config.authorized_callers)


def _require_positive(candidate: int, name: str) -> None:
    if candidate <= 0:
        raise ValueError(f"{name} must be positive")


def _require_prefetch(prefetch_count: int) -> None:
    if not 0 < prefetch_count <= 1024:
        raise ValueError("rabbitmq_prefetch_count must be between 1 and 1024")


def _require_authorized_callers(callers: frozenset[str]) -> None:
    if not callers:
        raise ValueError(
            "authorized_callers must contain at least one identity"
        )


@dataclass(frozen=True, slots=True)
class WorkflowConfig:
    """Deployment configuration for PostgreSQL and RabbitMQ integration."""

    database_url: str
    rabbitmq_url: str
    rabbitmq_tls_identity: TlsClientIdentity | None = None
    rabbitmq_exchange: str = "sird.workflow"
    rabbitmq_task_route: str = "sird.task.v1"
    rabbitmq_result_route: str = "sird.result.v1"
    rabbitmq_retry_route: str = "sird.task.retry.v1"
    rabbitmq_terminal_route: str = "sird.task.terminal.v1"
    authorized_callers: frozenset[str] = field(default_factory=frozenset)
    default_retention_seconds: int = DEFAULT_RETENTION_SECONDS
    max_attempts: int = 3
    rabbitmq_properties: Mapping[str, Any] = field(default_factory=dict)
    rabbitmq_prefetch_count: int = 8

    def __post_init__(self) -> None:
        if not self.database_url:
            raise ValueError("database_url must not be empty")
        if not self.rabbitmq_url:
            raise ValueError("rabbitmq_url must not be empty")
        scheme = urlsplit(self.rabbitmq_url).scheme.lower()
        if scheme != "amqps":
            raise ValueError("RabbitMQ transport must use TLS (amqps)")
        _validate_routes(self)
        _validate_limits(self)
