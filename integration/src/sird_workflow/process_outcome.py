"""Durable processing outcome value object."""

from dataclasses import dataclass

_ZERO_SECONDS = 0


@dataclass(frozen=True, slots=True)
class ProcessOutcome:
    """Durable outcome of processing one delivery."""

    task_id: str
    event_id: str
    status: str
    outcome: str
    attempt_number: int
    retry_after_seconds: float = _ZERO_SECONDS
    result_event_id: str | None = None
    dead_letter_event_id: str | None = None

    @property
    def terminal(self) -> bool:
        return self.result_event_id is not None
