"""Exceptions raised by dead-letter outbox transitions."""


class DeadLetterError(Exception):
    """Base class for dead-letter outbox failures."""


class PublicationNotAcknowledgedError(DeadLetterError):
    """A source offset cannot be committed before broker acknowledgement."""


class InvalidBrokerAcknowledgementError(DeadLetterError):
    """The broker acknowledgement does not belong to this event."""
