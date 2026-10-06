"""Typed dead-letter events and acknowledgement-gated outbox transitions."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, cast

from sird_workflow import _dead_letter_validation as validation
from sird_workflow._dead_letter_errors import (
    InvalidBrokerAcknowledgementError,
    PublicationNotAcknowledgedError,
)


class DeadLetterState(StrEnum):
    """Durable publication state for a dead-letter outbox row."""

    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"


@dataclass(frozen=True, slots=True)
class DeadLetterEvent:
    """One stable dead-letter event that can be published more than once."""

    event_id: str
    task_id: str
    topic: str
    payload: Mapping[str, Any]
    created_at: datetime

    def __post_init__(self) -> None:
        validation.require_text(self.event_id, "event_id")
        validation.require_text(self.task_id, "task_id")
        validation.require_text(self.topic, "topic")
        if not isinstance(self.payload, Mapping):
            raise TypeError("payload must be a mapping")


@dataclass(frozen=True, slots=True)
class BrokerAcknowledgement:
    """Explicit broker result returned by a dead-letter publisher."""

    event_id: str
    acknowledged: bool
    broker_message_id: str | None = None
    acknowledged_at: datetime | None = None

    def __post_init__(self) -> None:
        validation.require_text(self.event_id, "event_id")
        if self.broker_message_id is not None:
            validation.require_text(
                self.broker_message_id, "broker_message_id"
            )


class DeadLetterPublisher(Protocol):
    """Transport boundary for acknowledgement-returning publication."""

    def publish(self, event: DeadLetterEvent) -> BrokerAcknowledgement:
        """Publish an event and report whether the broker acknowledged it."""


PublisherCallable = Callable[[DeadLetterEvent], BrokerAcknowledgement]


def _outbox_task_id(outbox: Any) -> str:
    return outbox.event.task_id


@dataclass(frozen=True, slots=True)
class DeadLetterOutbox:
    """Durable-shaped dead-letter row with explicit commit gating.

    The row remains ``PENDING`` after an uncertain or negative broker result.
    A caller must explicitly invoke :meth:`commit_source_offset` after the row
    reaches ``ACKNOWLEDGED``.  This keeps source-offset ownership outside the
    publisher and prevents an unacknowledged publication from being committed.
    """

    event: DeadLetterEvent
    state: DeadLetterState = DeadLetterState.PENDING
    acknowledgement: BrokerAcknowledgement | None = None
    source_offset_committed: bool = False

    def __post_init__(self) -> None:
        if (
            self.state is DeadLetterState.PENDING
            and self.acknowledgement is not None
            and self.acknowledgement.acknowledged
        ):
            raise ValueError("acknowledged result requires acknowledged state")
        if self.state is DeadLetterState.ACKNOWLEDGED and (
            self.acknowledgement is None
            or not self.acknowledgement.acknowledged
        ):
            raise ValueError(
                "acknowledged state requires broker acknowledgement"
            )
        if (
            self.source_offset_committed
            and self.state is not DeadLetterState.ACKNOWLEDGED
        ):
            raise ValueError(
                "source offset cannot be committed while publication "
                "is pending"
            )

    @property
    def event_id(self) -> str:
        return self.event.event_id

    task_id = property(_outbox_task_id)

    @property
    def pending(self) -> bool:
        return self.state is DeadLetterState.PENDING

    @property
    def acknowledged(self) -> bool:
        return self.state is DeadLetterState.ACKNOWLEDGED

    def publish(
        self, publisher: DeadLetterPublisher | PublisherCallable
    ) -> DeadLetterOutbox:
        """Publish the stable event and record the explicit broker result."""

        publish_method = getattr(publisher, "publish", None)
        if callable(publish_method):
            publish = cast(PublisherCallable, publish_method)
            acknowledgement = publish(self.event)
        elif callable(publisher):
            publish = cast(PublisherCallable, publisher)
            acknowledgement = publish(self.event)
        else:
            raise TypeError("publisher must be callable or expose publish")
        return self.record_acknowledgement(acknowledgement)

    def record_acknowledgement(
        self, acknowledgement: BrokerAcknowledgement
    ) -> DeadLetterOutbox:
        """Apply a broker result without making an offset-commit decision."""

        if acknowledgement.event_id != self.event_id:
            raise InvalidBrokerAcknowledgementError(
                f"acknowledgement is for {acknowledgement.event_id!r}, "
                f"not {self.event_id!r}"
            )
        if not acknowledgement.acknowledged:
            return self
        return replace(
            self,
            state=DeadLetterState.ACKNOWLEDGED,
            acknowledgement=acknowledgement,
        )

    def commit_source_offset(self) -> DeadLetterOutbox:
        """Mark the source offset safe only after explicit broker
        acknowledgement."""

        if not self.acknowledged:
            raise PublicationNotAcknowledgedError(
                f"dead-letter event {self.event_id!r} has no broker "
                "acknowledgement"
            )
        return replace(self, source_offset_committed=True)

    mark_committed = commit_source_offset
