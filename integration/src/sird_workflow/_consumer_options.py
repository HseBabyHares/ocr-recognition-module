"""Optional dependency injection settings for the task consumer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sird_workflow.producer import RabbitMQTaskProducer

if TYPE_CHECKING:
    from sird_workflow._consumer_models import MessageAcknowledger


@dataclass(frozen=True, slots=True)
class _ConsumerOptions:
    """Optional consumer dependencies and transport settings."""

    acknowledger: MessageAcknowledger | None = None
    worker_id: str = "sird-task-consumer"
    engine: Any | None = None
    session_factory: Any | None = None
    consumer: Any | None = None
    retry_producer: RabbitMQTaskProducer | None = None

    @classmethod
    def parse(
        cls, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> _ConsumerOptions:
        option_names = (
            "acknowledger",
            "worker_id",
            "engine",
            "session_factory",
            "consumer",
            "retry_producer",
        )
        if len(args) > len(option_names):
            raise TypeError("too many positional consumer options")
        option_values = dict(zip(option_names, args, strict=False))
        overlap = option_values.keys() & kwargs.keys()
        if overlap:
            duplicate = next(iter(overlap))
            raise TypeError(f"multiple values for {duplicate!r}")
        option_values.update(kwargs)
        return cls(**option_values)
