"""Public transport models re-exported by :mod:`sird_workflow.consumer`."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol
from urllib.parse import urlsplit

from sird_workflow.mtls import TlsClientIdentity, tls_ssl_context


def _message_value_from_arguments(
    message_args: tuple[bytes | str | Mapping[str, Any], ...],
    message_options: dict[str, Any],
) -> bytes | str | Mapping[str, Any]:
    if len(message_args) > 1:
        raise TypeError("too many positional message arguments")
    if message_args and "value" in message_options:
        raise TypeError("multiple values for 'value'")
    if message_args:
        return message_args[0]
    try:
        return message_options.pop("value")
    except KeyError as exc:
        raise TypeError("missing required message argument: 'value'") from exc


@dataclass(frozen=True, slots=True)
class RabbitMQConsumerConfig:
    """AMQPS settings with bounded prefetch and manual acknowledgements."""

    amqp_url: str
    queue_name: str = "sird.task.v1"
    exchange_name: str = "sird.workflow"
    retry_route: str = "sird.task.retry.v1"
    prefetch_count: int = 8
    consumer_tag: str = "sird-task-consumer"
    tls_identity: TlsClientIdentity | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if urlsplit(self.amqp_url).scheme.lower() != "amqps":
            raise ValueError("RabbitMQ transport must use TLS (amqps)")
        if (
            not self.queue_name
            or not self.exchange_name
            or not self.retry_route
        ):
            raise ValueError(
                "queue_name, exchange_name, and retry_route must not be empty"
            )
        if not 0 < self.prefetch_count <= 1024:
            raise ValueError("prefetch_count must be between 1 and 1024")

    def connection_kwargs(self) -> dict[str, Any]:
        connection_options: dict[str, Any] = {
            "client_properties": {"connection_name": self.consumer_tag}
        }
        if self.tls_identity is not None:
            connection_options["ssl_context"] = tls_ssl_context(
                self.tls_identity
            )
        connection_options.update(self.extra)
        return connection_options


@dataclass(frozen=True, slots=True, init=False)
class TaskConsumerMessage:
    """Transport fields required to process one RabbitMQ delivery."""

    routing_key: str
    delivery_tag: int
    key: str | bytes | None
    _message_value: bytes | str | Mapping[str, Any]
    message_id: str | None
    redelivered: bool

    def __init__(
        self,
        routing_key: str,
        delivery_tag: int,
        **message_options: Any,
    ) -> None:
        key = message_options.pop("key", None)
        message_id = message_options.pop("message_id", None)
        redelivered = message_options.pop("redelivered", False)
        message_value = _message_value_from_arguments((), message_options)
        if message_options:
            unexpected = next(iter(message_options))
            raise TypeError(f"unexpected message argument: {unexpected!r}")
        object.__setattr__(self, "routing_key", routing_key)
        object.__setattr__(self, "delivery_tag", delivery_tag)
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "_message_value", message_value)
        object.__setattr__(self, "message_id", message_id)
        object.__setattr__(self, "redelivered", redelivered)

    @property
    def payload(self) -> bytes | str | Mapping[str, Any]:
        """Return the message payload."""
        return self._message_value


type.__setattr__(
    TaskConsumerMessage,
    "value",
    property(TaskConsumerMessage.payload.fget),
)


class MessageAcknowledger(Protocol):
    """Injected acknowledgement boundary for focused delivery tests."""

    def __call__(self, message: Any) -> None:
        """Acknowledge only after all durable workflow state is ready."""


class OffsetCommitter(MessageAcknowledger, Protocol):
    """Compatibility-neutral name for an injected source acknowledgement."""


class TaskConsumerDecision(StrEnum):
    """Outcome of one bounded task-message handling pass."""

    RETRY_WITHOUT_ACK = "retry_without_ack"
    TERMINAL_ACK_READY = "terminal_ack_ready"
    INVALID_EVENT = "invalid_event"

    RETRY_WITHOUT_COMMIT = "retry_without_ack"
    TERMINAL_COMMIT_READY = "terminal_ack_ready"
