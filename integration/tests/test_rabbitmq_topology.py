from __future__ import annotations

import asyncio

from sird_workflow._producer_support import (
    RESULT_ROUTE,
    RETRY_ROUTE,
    TASK_ROUTE,
    TERMINAL_ROUTE,
    _Topology,
)


class BindingProbe:
    def __init__(self) -> None:
        self.calls: list[tuple[object, str]] = []

    async def bind(self, target: object, *, routing_key: str) -> None:
        self.calls.append((target, routing_key))


def test_topology_binds_queues_to_exchanges() -> None:
    exchange = BindingProbe()
    dead_letter_exchange = BindingProbe()
    queues = {
        route: BindingProbe()
        for route in (TASK_ROUTE, RESULT_ROUTE, RETRY_ROUTE, TERMINAL_ROUTE)
    }

    asyncio.run(_Topology.bind(exchange, dead_letter_exchange, queues))

    assert exchange.calls == []
    assert dead_letter_exchange.calls == []
    assert {route: queue.calls for route, queue in queues.items()} == {
        TASK_ROUTE: [(exchange, TASK_ROUTE)],
        RESULT_ROUTE: [(exchange, RESULT_ROUTE)],
        RETRY_ROUTE: [(exchange, RETRY_ROUTE)],
        TERMINAL_ROUTE: [
            (exchange, TERMINAL_ROUTE),
            (dead_letter_exchange, TERMINAL_ROUTE),
        ],
    }
