"""Private RabbitMQ topology and confirmation helpers."""

from __future__ import annotations

import asyncio
from typing import Any

import aio_pika

from sird_workflow.exceptions import PublicationFailureError

DEAD_LETTER_EXCHANGE = "sird.workflow.dlx"
RESULT_ROUTE = "sird.result.v1"
RETRY_ROUTE = "sird.task.retry.v1"
TASK_ROUTE = "sird.task.v1"
TERMINAL_ROUTE = "sird.task.terminal.v1"


class UnroutableMessageError(PublicationFailureError):
    """RabbitMQ returned a mandatory publication without a route."""


class PublisherConfirmationError(PublicationFailureError):
    """RabbitMQ rejected or timed out a publisher confirmation."""


class _Topology:
    @classmethod
    async def exchanges(
        cls, channel: Any, exchange_name: str
    ) -> tuple[Any, Any]:
        exchange = await channel.declare_exchange(
            exchange_name, type=aio_pika.ExchangeType.DIRECT, durable=True
        )
        dead_letter_exchange = await channel.declare_exchange(
            DEAD_LETTER_EXCHANGE,
            type=aio_pika.ExchangeType.DIRECT,
            durable=True,
        )
        return exchange, dead_letter_exchange

    @classmethod
    async def queues(cls, channel: Any, exchange_name: str) -> dict[str, Any]:
        queue_args = {"x-queue-type": "quorum"}
        task_queue = await channel.declare_queue(
            TASK_ROUTE,
            durable=True,
            arguments={
                **queue_args,
                "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE,
                "x-dead-letter-routing-key": TERMINAL_ROUTE,
            },
        )
        result_queue = await channel.declare_queue(
            RESULT_ROUTE, durable=True, arguments=queue_args
        )
        retry_queue = await channel.declare_queue(
            RETRY_ROUTE,
            durable=True,
            arguments={
                **queue_args,
                "x-message-ttl": 1_000,
                "x-dead-letter-exchange": exchange_name,
                "x-dead-letter-routing-key": TASK_ROUTE,
            },
        )
        terminal_queue = await channel.declare_queue(
            TERMINAL_ROUTE, durable=True, arguments=queue_args
        )
        return {
            TASK_ROUTE: task_queue,
            RESULT_ROUTE: result_queue,
            RETRY_ROUTE: retry_queue,
            TERMINAL_ROUTE: terminal_queue,
        }

    async def bind(
        exchange: Any, dead_letter_exchange: Any, queues: dict[str, Any]
    ) -> None:
        await asyncio.gather(
            *(
                queue.bind(exchange, routing_key=route)
                for route, queue in queues.items()
            )
        )
        await queues[TERMINAL_ROUTE].bind(
            dead_letter_exchange, routing_key=TERMINAL_ROUTE
        )


class _Publication:
    @classmethod
    def error(
        cls, exc: Exception, routing_key: str
    ) -> PublicationFailureError:
        error_name = type(exc).__name__.lower()
        error_text = str(exc).lower()
        if (
            "deliveryerror" in error_name
            or "unrout" in error_name
            or "return" in error_text
        ):
            route = repr(routing_key)
            return UnroutableMessageError(
                f"RabbitMQ publication was unroutable for route {route}"
            )
        return PublisherConfirmationError(
            f"RabbitMQ publication was not confirmed for route {routing_key!r}"
        )

    @classmethod
    def check(cls, publication: Any, routing_key: str) -> None:
        publication_name = type(publication).__name__.lower()
        if publication_name in {
            "returnedmessage",
            "returnmessage",
            "deliveredmessage",
        }:
            route = repr(routing_key)
            raise UnroutableMessageError(
                f"RabbitMQ publication was unroutable for route {route}"
            )
        if publication is False:
            raise PublisherConfirmationError(
                f"RabbitMQ publication was rejected for route {routing_key!r}"
            )

    @classmethod
    async def confirmed(
        cls,
        exchange: Any,
        message: Any,
        *,
        routing_key: str,
        timeout_seconds: float,
    ) -> None:
        try:
            publication = await asyncio.wait_for(
                exchange.publish(
                    message, routing_key=routing_key, mandatory=True
                ),
                timeout=timeout_seconds,
            )
        except Exception as exc:
            raise cls.error(exc, routing_key) from exc
        cls.check(publication, routing_key)


publish_confirmed = _Publication.confirmed
