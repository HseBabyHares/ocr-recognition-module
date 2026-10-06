from __future__ import annotations

from datetime import datetime

import pytest
from sird_workflow.attempts import (
    AttemptBudget,
    AttemptBudgetExhaustedError,
    DuplicateTerminalTransitionError,
    StaleAttemptLeaseError,
)
from sird_workflow.dead_letter import (
    BrokerAcknowledgement,
    DeadLetterEvent,
    DeadLetterOutbox,
    DeadLetterState,
    PublicationNotAcknowledgedError,
)

REFERENCE_TIME = datetime.fromisoformat("2030-01-01T00:00:00+00:00")
DELIVERY_ONE = "delivery-1"
FAILED_OUTCOME = "failed"


class Publisher:
    def __init__(self) -> None:
        self.event_ids: list[str] = []

    def publish(self, event: DeadLetterEvent) -> BrokerAcknowledgement:
        self.event_ids.append(event.event_id)
        return BrokerAcknowledgement(
            event_id=event.event_id, acknowledged=True
        )


def test_shared_budget_counts_replay_once() -> None:
    budget = AttemptBudget(task_id="task-1")

    budget, first = budget.claim("worker-a", delivery_id=DELIVERY_ONE)
    budget, replayed = budget.claim("worker-b", delivery_id=DELIVERY_ONE)

    assert budget.attempts_used == 1
    assert replayed.attempt_number == first.attempt_number
    assert replayed.fencing_token > first.fencing_token

    budget = budget.release(replayed)
    budget, second = budget.claim("worker-b", delivery_id="delivery-2")
    budget = budget.release(second)
    budget, third = budget.claim("worker-c", delivery_id="delivery-3")
    assert (
        first.attempt_number,
        second.attempt_number,
        third.attempt_number,
    ) == (1, 2, 3)

    with pytest.raises(AttemptBudgetExhaustedError):
        budget.claim("worker-d", delivery_id="delivery-4")


def test_stale_lease_rejected_after_fencing() -> None:
    budget, stale_lease = AttemptBudget(task_id="task-2").claim(
        "worker-a", delivery_id=DELIVERY_ONE
    )
    budget = budget.release(stale_lease)
    budget, current_lease = budget.claim("worker-b", delivery_id="delivery-2")

    with pytest.raises(StaleAttemptLeaseError):
        budget.complete(stale_lease, outcome=FAILED_OUTCOME)

    budget = budget.complete(current_lease, outcome=FAILED_OUTCOME)
    assert budget.terminal_outcome == FAILED_OUTCOME


def test_repeated_terminal_transition_rejected() -> None:
    budget, lease = AttemptBudget(task_id="task-3").claim(
        "worker-a", delivery_id=DELIVERY_ONE
    )
    budget = budget.complete(lease, outcome=FAILED_OUTCOME)

    with pytest.raises(DuplicateTerminalTransitionError):
        budget.complete(lease, outcome=FAILED_OUTCOME)


def test_dead_letter_republication_preserves_id() -> None:
    event = DeadLetterEvent(
        event_id="dlq-event-1",
        task_id="task-4",
        topic="sird.task.dlq.v1",
        payload={"task_id": "task-4", "reason": "budget_exhausted"},
        created_at=REFERENCE_TIME,
    )
    outbox = DeadLetterOutbox(event=event)

    publisher = Publisher()
    outbox = outbox.publish(publisher)
    outbox = DeadLetterOutbox(event=event).publish(publisher)

    assert publisher.event_ids == ["dlq-event-1", "dlq-event-1"]
    assert outbox.event_id == event.event_id
    assert outbox.state is DeadLetterState.ACKNOWLEDGED


def test_unacknowledged_publish_prevents_commit() -> None:
    event = DeadLetterEvent(
        event_id="dlq-event-2",
        task_id="task-5",
        topic="sird.task.dlq.v1",
        payload={"task_id": "task-5"},
        created_at=REFERENCE_TIME,
    )
    outbox = DeadLetterOutbox(event=event).publish(
        lambda event: BrokerAcknowledgement(
            event_id=event.event_id, acknowledged=False
        )
    )

    assert outbox.state is DeadLetterState.PENDING
    with pytest.raises(PublicationNotAcknowledgedError):
        outbox.commit_source_offset()


def test_acknowledged_publish_allows_commit() -> None:
    event = DeadLetterEvent(
        event_id="dlq-event-3",
        task_id="task-6",
        topic="sird.task.dlq.v1",
        payload={"task_id": "task-6"},
        created_at=REFERENCE_TIME,
    )
    outbox = DeadLetterOutbox(event=event).publish(
        lambda event: BrokerAcknowledgement(
            event_id=event.event_id, acknowledged=True
        )
    )

    committed = outbox.commit_source_offset()
    assert committed.source_offset_committed is True
