from __future__ import annotations

import test_consumer_constants as ConsumerConstants
from sird_workflow.ocr_outcome import OcrOutcome
from sird_workflow.process_outcome import ProcessOutcome
from sird_workflow.task_event import TaskEvent


def _terminal_outcome(event: TaskEvent) -> ProcessOutcome:
    return ProcessOutcome(
        task_id=event.task_id,
        event_id=event.event_id,
        status="succeeded",
        outcome=OcrOutcome.SUCCESS.value,
        attempt_number=1,
        result_event_id=ConsumerConstants.RESULT_EVENT_ID,
    )


def _failed_outcome(event: TaskEvent) -> ProcessOutcome:
    return ProcessOutcome(
        task_id=event.task_id,
        event_id=event.event_id,
        status="failed",
        outcome=OcrOutcome.PERMANENT.value,
        attempt_number=1,
        result_event_id=ConsumerConstants.RESULT_EVENT_ID,
        dead_letter_event_id=ConsumerConstants.DEAD_LETTER_EVENT_ID,
    )


def _retrying_outcome(event: TaskEvent) -> ProcessOutcome:
    return ProcessOutcome(
        task_id=event.task_id,
        event_id=event.event_id,
        status="retrying",
        outcome=OcrOutcome.TRANSIENT.value,
        attempt_number=1,
    )


def _cancelled_outcome(event: TaskEvent) -> ProcessOutcome:
    return ProcessOutcome(
        task_id=event.task_id,
        event_id=event.event_id,
        status="cancelled",
        outcome=OcrOutcome.CANCELLED.value,
        attempt_number=1,
        result_event_id=f"{event.event_id}:result",
        dead_letter_event_id=f"{event.event_id}:dead-letter",
    )


def _retry_outcome(event: TaskEvent) -> ProcessOutcome:
    return ProcessOutcome(
        task_id=event.task_id,
        event_id=event.event_id,
        status="retrying",
        outcome=OcrOutcome.TRANSIENT.value,
        attempt_number=1,
    )


def _success_outcome(event: TaskEvent) -> ProcessOutcome:
    return ProcessOutcome(
        task_id=event.task_id,
        event_id=event.event_id,
        status="succeeded",
        outcome=OcrOutcome.SUCCESS.value,
        attempt_number=1,
        result_event_id=f"{event.event_id}:result",
    )
