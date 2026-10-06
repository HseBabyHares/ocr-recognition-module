"""In-memory retry suppression for delivery positions."""

from __future__ import annotations

import time

from sird_workflow._consumer_state import _ConsumerState


class _ConsumerPosition(_ConsumerState):
    """Track deliveries temporarily blocked from immediate reprocessing."""

    def _blocked(self, position: str | None) -> bool:
        if position is None:
            return False
        blocked_until = self._blocked_ids.get(position)
        if blocked_until is None:
            return False
        if blocked_until <= time.monotonic():
            self._blocked_ids.pop(position, None)
            return False
        return True

    def _block(
        self, position: str | None, *, delay_seconds: float = 0
    ) -> None:
        if position is None:
            return
        effective_delay = delay_seconds if delay_seconds > 0 else 1.0
        self._blocked_ids[position] = time.monotonic() + effective_delay

    def _clear_position(self, position: str | None) -> None:
        if position is not None:
            self._blocked_ids.pop(position, None)
