"""Composition of private consumer operation mixins."""

from sird_workflow._consumer_decoder import _ConsumerDecoder
from sird_workflow._consumer_delivery import _ConsumerDelivery
from sird_workflow._consumer_lifecycle import _ConsumerLifecycle
from sird_workflow._consumer_persistence import _ConsumerPersistence
from sird_workflow._consumer_position import _ConsumerPosition
from sird_workflow._consumer_transport import _ConsumerTransport


class _ConsumerTransportDelivery(
    _ConsumerLifecycle,
    _ConsumerTransport,
    _ConsumerDelivery,
):
    """Lifecycle, transport, and delivery operations."""


class _ConsumerProcessing(
    _ConsumerPosition,
    _ConsumerDecoder,
    _ConsumerPersistence,
):
    """Position, decoding, and persistence operations."""


class _ConsumerOperations(_ConsumerTransportDelivery, _ConsumerProcessing):
    """Complete consumer operation surface."""
