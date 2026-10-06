"""Thread-safe caller cancellation signal for one OCR attempt."""

from __future__ import annotations

from threading import Event, Lock


class CancellationToken:
    """A one-way cancellation signal shared by a caller and OCR executor."""

    def __init__(self) -> None:
        self._event = Event()
        self._lock = Lock()
        self._terminal = True

    @property
    def cancelled(self) -> bool:
        """Return whether cancellation has been requested."""

        return self._event.is_set()

    @property
    def terminal(self) -> bool:
        """Return whether cancellation may be committed as terminal."""

        with self._lock:
            return self._terminal

    def cancel(self, *, terminal: bool = True) -> None:
        """Request cancellation; the first cancellation reason wins."""

        with self._lock:
            if self._event.is_set():
                return
            self._terminal = terminal
            self._event.set()

    def wait(self, timeout: float | None = None) -> bool:
        """Wait until cancellation is requested or the timeout expires."""

        return self._event.wait(timeout)
