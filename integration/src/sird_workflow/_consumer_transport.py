"""RabbitMQ connection and queue declaration operations."""

from __future__ import annotations

from typing import Any

import aio_pika

from sird_workflow._consumer_state import _ConsumerState
from sird_workflow.producer import declare_topology


class _ConsumerTransport(_ConsumerState):
    """Connection and queue setup for a task consumer."""

    @classmethod
    def _delivery_route(cls, delivery: Any) -> Any:
        route = getattr(delivery, "routing_key", None)
        if route is None:
            return getattr(delivery, "topic", None)
        return route

    async def _connect(self) -> None:
        connection = await aio_pika.connect_robust(
            self._config.amqp_url, **self._config.connection_kwargs()
        )
        channel = await connection.channel()
        self._connection = connection
        self._channel = channel
        await channel.set_qos(prefetch_count=self._config.prefetch_count)

    async def _declare_queue(self) -> None:
        channel = self._channel
        if channel is None:
            raise RuntimeError("consumer channel is not connected")
        await declare_topology(channel, self._config.exchange_name)
        self._queue = await channel.declare_queue(
            self._config.queue_name,
            durable=True,
            arguments={
                "x-queue-type": "quorum",
                "x-dead-letter-exchange": "sird.workflow.dlx",
                "x-dead-letter-routing-key": "sird.task.terminal.v1",
            },
        )

    async def _start_consuming(self) -> None:
        queue = self._queue
        if queue is None:
            raise RuntimeError("consumer queue is not declared")
        self._consumer = await queue.consume(
            self._consume_delivery,
            consumer_tag=self._config.consumer_tag,
            no_ack=False,
        )
