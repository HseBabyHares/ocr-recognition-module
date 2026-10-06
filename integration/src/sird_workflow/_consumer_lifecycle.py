"""Lifecycle operations for a bounded RabbitMQ task consumer."""

from __future__ import annotations

import inspect
from typing import Any

from sird_workflow._consumer_state import _ConsumerState


class _ConsumerLifecycle(_ConsumerState):
    """Connection and revocation operations for the task consumer."""

    async def start(self) -> None:
        if self._retry_producer is None:
            self._retry_producer = self._create_retry_producer()
        await self._connect()
        await self._declare_queue()
        await self._start_consuming()

    def subscribe(self, routes: Any, **kwargs: Any) -> None:
        options = dict(kwargs)
        options.setdefault("on_revoke", self._on_revoke)
        subscribe = getattr(self._consumer, "subscribe", None)
        if callable(subscribe):
            subscribe(routes, **options)

    def on_revoke(self, _consumer: Any, deliveries: Any) -> None:
        revoked_routes = {
            self._delivery_route(delivery) for delivery in deliveries
        }
        for position, token in tuple(self._active_cancellations.items()):
            route = position[0] if isinstance(position, tuple) else None
            if route in revoked_routes or isinstance(position, str):
                token.cancel(terminal=False)

    def close(self) -> None:
        for token in tuple(self._active_cancellations.values()):
            token.cancel(terminal=False)
        close = getattr(self._consumer, "close", None)
        if callable(close) and not inspect.iscoroutinefunction(close):
            close()

    async def close_async(self) -> None:
        self.close()
        if self._connection is not None:
            await self._connection.close()
        self._connection = None
        self._channel = None
        self._queue = None

    async def _consume_delivery(self, message: Any) -> None:
        await self.handle_delivery(message)

    def _on_revoke(self, _consumer: Any, deliveries: Any) -> None:
        self.on_revoke(_consumer, deliveries)
