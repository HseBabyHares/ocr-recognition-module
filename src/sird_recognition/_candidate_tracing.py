"""Private tracemalloc lifecycle helper for candidate inference."""

from __future__ import annotations

import tracemalloc


class TracingPeak:
    """Keep a tracing session active for one candidate inference."""

    def __init__(self) -> None:
        self._started_here = False

    def __enter__(self) -> TracingPeak:
        self._started_here = not tracemalloc.is_tracing()
        if self._started_here:
            tracemalloc.start()
        tracemalloc.reset_peak()
        return self

    def __exit__(self, *_: object) -> None:
        if self._started_here:
            tracemalloc.stop()
