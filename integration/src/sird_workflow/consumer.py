"""Bounded RabbitMQ task consumption with durable manual acknowledgements."""

from typing import Any

from sird_workflow._consumer_composition import _ConsumerOperations
from sird_workflow._consumer_models import (
    MessageAcknowledger as _MessageAcknowledger,
)
from sird_workflow._consumer_models import (
    OffsetCommitter as _OffsetCommitter,
)
from sird_workflow._consumer_models import (
    RabbitMQConsumerConfig as _RabbitMQConsumerConfig,
)
from sird_workflow._consumer_models import (
    TaskConsumerDecision as _TaskConsumerDecision,
)
from sird_workflow._consumer_models import (
    TaskConsumerMessage as _TaskConsumerMessage,
)
from sird_workflow._consumer_options import _ConsumerOptions
from sird_workflow.cancellation import CancellationToken
from sird_workflow.process import ProcessService
from sird_workflow.process_outbox import ProcessOutboxDispatcher
from sird_workflow.producer import RabbitMQProducerConfig, RabbitMQTaskProducer

MessageAcknowledger = _MessageAcknowledger
OffsetCommitter = _OffsetCommitter
RabbitMQConsumerConfig = _RabbitMQConsumerConfig
TaskConsumerDecision = _TaskConsumerDecision
TaskConsumerMessage = _TaskConsumerMessage


class RabbitMQTaskConsumer(_ConsumerOperations):
    """Process one RabbitMQ delivery without owning business state."""

    def __init__(
        self,
        config: RabbitMQConsumerConfig,
        process_service: ProcessService,
        outbox_dispatcher: ProcessOutboxDispatcher,
        *consumer_args: Any,
        **consumer_kwargs: Any,
    ) -> None:
        consumer_options = _ConsumerOptions.parse(
            consumer_args, consumer_kwargs
        )
        self._config = config
        self._process_service = process_service
        self._outbox_dispatcher = outbox_dispatcher
        self._worker_id = consumer_options.worker_id
        self._consumer = consumer_options.consumer
        self._connection: Any | None = None
        self._channel: Any | None = None
        self._queue: Any | None = None
        self._retry_producer = consumer_options.retry_producer
        self._acknowledger = (
            consumer_options.acknowledger or self._ack_with_message
        )
        self._blocked_ids: dict[str, float] = {}
        self._active_cancellations: dict[object, CancellationToken] = {}
        self._decision_type = TaskConsumerDecision
        self._session_factory = self._resolve_session_factory(
            engine=consumer_options.engine,
            session_factory=consumer_options.session_factory,
        )

    @property
    def consumer(self) -> Any:
        """Expose the delivery client for an application-owned loop."""
        return self._consumer

    def _create_retry_producer(self) -> RabbitMQTaskProducer:
        return RabbitMQTaskProducer(
            RabbitMQProducerConfig(
                amqp_url=self._config.amqp_url,
                exchange_name=self._config.exchange_name,
                tls_identity=self._config.tls_identity,
                extra=self._config.extra,
            )
        )
