"""RabbitMQ task-event publication with confirmation and route checks."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import urlsplit

import aio_pika

from sird_workflow._producer_support import (
    _Topology,
    publish_confirmed,
)
from sird_workflow.dead_letter import BrokerAcknowledgement, DeadLetterEvent
from sird_workflow.exceptions import PublicationFailureError
from sird_workflow.mtls import TlsClientIdentity, tls_ssl_context

WORKFLOW_EXCHANGE = "sird.workflow"
DEAD_LETTER_EXCHANGE = "sird.workflow.dlx"
TASK_ROUTE = "sird.task.v1"
RESULT_ROUTE = "sird.result.v1"
RETRY_ROUTE = "sird.task.retry.v1"
TERMINAL_ROUTE = "sird.task.terminal.v1"


class TaskProducer(Protocol):
    """Transport boundary used by the durable workflow service."""

    def publish(
        self, *, topic: str, key: str, payload: Mapping[str, Any]
    ) -> None:
        """Publish one event and return only after broker confirmation."""


@dataclass(frozen=True, slots=True)
class RabbitMQProducerConfig:
    """AMQPS settings for a confirmed, persistent RabbitMQ publisher."""

    amqp_url: str
    exchange_name: str = WORKFLOW_EXCHANGE
    client_id: str = "sird-task-service"
    publish_timeout_seconds: float = 10.0
    tls_identity: TlsClientIdentity | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if urlsplit(self.amqp_url).scheme.lower() != "amqps":
            raise ValueError("RabbitMQ transport must use TLS (amqps)")
        if not self.exchange_name:
            raise ValueError("exchange_name must not be empty")
        if self.publish_timeout_seconds <= 0:
            raise ValueError("publish_timeout_seconds must be positive")

    def connection_kwargs(self) -> dict[str, Any]:
        """Return safe connection settings for ``aio_pika.connect_robust``."""
        kwargs: dict[str, Any] = {
            "client_properties": {"connection_name": self.client_id},
        }
        if self.tls_identity is not None:
            kwargs["ssl_context"] = tls_ssl_context(self.tls_identity)
        kwargs.update(self.extra)
        return kwargs


class RabbitMQTaskProducer:
    """Synchronous facade over a long-lived aio-pika confirmed publisher."""

    def __init__(self, config: RabbitMQProducerConfig) -> None:
        self._config = config
        self._runner = asyncio.Runner()
        self._connection: Any | None = None
        self._channel: Any | None = None
        self._exchange: Any | None = None

    @classmethod
    async def declare_topology(
        cls, channel: Any, exchange_name: str = WORKFLOW_EXCHANGE
    ) -> None:
        """Declare durable exchanges, queues, bindings, and retry routing."""
        exchange, dead_letter_exchange = await _Topology.exchanges(
            channel, exchange_name
        )
        queues = await _Topology.queues(channel, exchange_name)
        await _Topology.bind(exchange, dead_letter_exchange, queues)

    def publish(
        self, *, topic: str, key: str, payload: Mapping[str, Any]
    ) -> None:
        """Publish a persistent event and wait for confirmation and routing."""
        self._runner.run(
            self.publish_async(topic=topic, key=key, payload=payload)
        )

    async def publish_async(
        self, *, topic: str, key: str, payload: Mapping[str, Any]
    ) -> None:
        """Async publication seam for application-owned event loops and
        tests."""
        await self._ensure_channel(aio_pika)
        assert self._exchange is not None
        event_id = self._text(payload.get("event_id"), "event_id")
        event_type = self._text(payload.get("event_type"), "event_type")
        request_id = self._text(payload.get("request_id"), "request_id")
        body = json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode()
        message = aio_pika.Message(
            body=body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=event_id,
            type=event_type,
            correlation_id=request_id,
            content_type="application/json",
            content_encoding="utf-8",
            headers={
                "schema_version": event_type.rsplit(".", 1)[-1],
                "task_id": key,
                "request_id": request_id,
            },
        )
        await publish_confirmed(
            self._exchange,
            message,
            routing_key=topic,
            timeout_seconds=self._config.publish_timeout_seconds,
        )

    def close(self) -> None:
        """Close the app-owned AMQP connection and event loop."""
        if self._connection is not None:
            self._runner.run(self._connection.close())
        self._runner.close()
        self._connection = None
        self._channel = None
        self._exchange = None

    async def _ensure_channel(self, aio_pika_module: Any) -> None:
        if self._exchange is not None:
            return
        self._connection = await aio_pika_module.connect_robust(
            self._config.amqp_url, **self._config.connection_kwargs()
        )
        self._channel = await self._connection.channel(publisher_confirms=True)
        await declare_topology(self._channel, self._config.exchange_name)
        self._exchange = await self._channel.get_exchange(
            self._config.exchange_name, ensure=True
        )

    @classmethod
    def _text(cls, candidate: object, name: str) -> str:
        if not isinstance(candidate, str) or not candidate.strip():
            raise PublicationFailureError(
                f"{name} must be present in the event payload"
            )
        return candidate


declare_topology = RabbitMQTaskProducer.declare_topology


class RabbitMQDeadLetterPublisher:
    """Publish terminal events through the same confirmed RabbitMQ boundary."""

    def __init__(self, producer: RabbitMQTaskProducer) -> None:
        self._producer = producer

    def publish(self, event: DeadLetterEvent) -> BrokerAcknowledgement:
        self._producer.publish(
            topic=event.topic,
            key=event.task_id,
            payload=event.payload,
        )
        return BrokerAcknowledgement(
            event_id=event.event_id,
            acknowledged=True,
            broker_message_id=event.event_id,
        )
