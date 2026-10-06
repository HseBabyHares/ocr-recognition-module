from __future__ import annotations

from typing import Any


class TransportConfig:
    publish_timeout_seconds = 1
    prefetch_limit = 8
    second_delivery_tag = 2


class ConfirmationFailureExchange:
    async def publish(self, _message: Any, **_kwargs: Any) -> None:
        raise RuntimeError("publisher confirm failed")


class UnroutableExchange:
    async def publish(self, _message: Any, **_kwargs: Any) -> None:
        error = type("DeliveryError", (RuntimeError,), {})
        raise error("mandatory message returned")


class ReturnedDeliveryExchange:
    async def publish(self, _message: Any, **_kwargs: Any) -> Any:
        return type("DeliveredMessage", (), {})()


class Delivery:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    async def ack(self) -> None:
        self.events.append("ack")
