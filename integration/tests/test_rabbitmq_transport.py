from __future__ import annotations

import asyncio
from typing import cast

import pytest
from rabbitmq_transport_support import (
    ConfirmationFailureExchange,
    Delivery,
    ReturnedDeliveryExchange,
    TransportConfig,
    UnroutableExchange,
)
from sird_workflow._consumer_models import TaskConsumerMessage
from sird_workflow._producer_support import (
    PublisherConfirmationError,
    UnroutableMessageError,
    publish_confirmed,
)
from sird_workflow.consumer import (
    RabbitMQConsumerConfig,
    RabbitMQTaskConsumer,
    TaskConsumerDecision,
)


def test_returned_delivery_is_explicit() -> None:
    with pytest.raises(UnroutableMessageError):
        asyncio.run(
            publish_confirmed(
                ReturnedDeliveryExchange(),
                object(),
                routing_key="sird.missing.v1",
                timeout_seconds=TransportConfig.publish_timeout_seconds,
            )
        )


def test_confirmation_failure_is_explicit() -> None:
    with pytest.raises(PublisherConfirmationError):
        asyncio.run(
            publish_confirmed(
                ConfirmationFailureExchange(),
                object(),
                routing_key="sird.task.v1",
                timeout_seconds=TransportConfig.publish_timeout_seconds,
            )
        )


def test_unroutable_return_is_explicit() -> None:
    with pytest.raises(UnroutableMessageError):
        asyncio.run(
            publish_confirmed(
                UnroutableExchange(),
                object(),
                routing_key="sird.missing.v1",
                timeout_seconds=TransportConfig.publish_timeout_seconds,
            )
        )


def test_redelivery_keeps_stable_message_identity() -> None:
    first = TaskConsumerMessage(
        routing_key="sird.task.v1",
        delivery_tag=TransportConfig.publish_timeout_seconds,
        value=cast(dict[str, object], {"event_id": "event-1"}),
        message_id="event-1",
    )
    redelivery = TaskConsumerMessage(
        routing_key=first.routing_key,
        delivery_tag=TransportConfig.second_delivery_tag,
        key=first.key,
        value=cast(dict[str, object], getattr(first, "value", None)),
        message_id=first.message_id,
        redelivered=True,
    )
    assert redelivery.message_id == first.message_id
    assert redelivery.redelivered is True


def test_prefetch_is_bounded() -> None:
    config = RabbitMQConsumerConfig(
        "amqps://localhost:5671/sird",
        prefetch_count=TransportConfig.prefetch_limit,
    )
    assert config.prefetch_count == TransportConfig.prefetch_limit
    with pytest.raises(ValueError):
        RabbitMQConsumerConfig("amqps://localhost:5671/sird", prefetch_count=0)


def test_ack_runs_after_durable_handler() -> None:
    events: list[str] = []
    consumer = object.__new__(RabbitMQTaskConsumer)
    consumer._retry_producer = None
    consumer.handle_message = lambda *_args, **_kwargs: (
        events.append("durable") or TaskConsumerDecision.TERMINAL_ACK_READY
    )
    asyncio.run(consumer.handle_delivery(Delivery(events)))
    assert events == ["durable", "ack"]
