"""Executable workflow contract oracles."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sird_verification.adapters import (
    AdapterUnavailableError,
    ArtifactCapabilityAdapter,
    AttemptBudgetAdapter,
    DeadLetterAdapter,
)
from sird_verification.contracts import OracleResult, OracleStatus
from sird_verification._oracle_support import (
    blocked,
    build_result,
    is_ack_gate_error,
    is_capability_rejection,
)

_REJECTED = "rejected"
_PUBLICATION_OBSERVED = "publication_observed"
_ACKNOWLEDGED = "acknowledged"
_OFFSET_COMMIT_BLOCKED = "offset_commit_blocked"
_OFFSET_COMMIT_ALLOWED = "offset_commit_allowed"
_OUTBOX_ORACLE_ID = "workflow.outbox-dlt-ack-gating"
_REQUIRED_CAPABILITY_FIELDS = ("task_id", "request_id", "artifact")
_MISSING_CAPABILITY_EVIDENCE = "required capability evidence is absent"
_MISSING_ATTEMPT_EVIDENCE = "required attempt-budget evidence is absent"
_MISSING_DEAD_LETTER_EVIDENCE = "required dead-letter evidence is absent"


def artifact_capability_rejection_oracle(
    adapter: ArtifactCapabilityAdapter | None,
    token: str | None,
    **details: Any,
) -> OracleResult:
    """Prove that an invalid capability is rejected before artifact access."""
    oracle_id = "artifact.capability-rejection"
    if not _has_capability_evidence(adapter, token, details):
        return blocked(oracle_id, _MISSING_CAPABILITY_EVIDENCE)
    try:
        adapter.validate(token, **details)
    except AdapterUnavailableError:
        return blocked(oracle_id, "capability validator is unavailable")
    except Exception as error:
        if is_capability_rejection(error):
            return build_result(
                oracle_id,
                OracleStatus.PASS,
                {_REJECTED: True},
                "capability validation rejected the request",
            )
        return build_result(
            oracle_id,
            OracleStatus.FAIL,
            {_REJECTED: False},
            "capability validation raised an unexpected error",
        )
    return build_result(
        oracle_id,
        OracleStatus.FAIL,
        {_REJECTED: False},
        "invalid capability was accepted",
    )


def shared_attempt_budget_oracle(
    adapter: AttemptBudgetAdapter | None,
    *,
    worker_id: str = "worker-a",
    takeover_worker_id: str = "worker-b",
    delivery_id: str = "delivery-1",
) -> OracleResult:
    """Prove duplicate delivery does not consume a second shared attempt."""
    oracle_id = "workflow.shared-attempt-budget"
    if adapter is None:
        return blocked(oracle_id, _MISSING_ATTEMPT_EVIDENCE)
    try:
        observed = _shared_attempt_observation(
            adapter,
            worker_id,
            takeover_worker_id,
            delivery_id,
        )
    except AdapterUnavailableError:
        return blocked(oracle_id, "attempt-budget adapter is unavailable")
    except Exception:
        return build_result(
            oracle_id,
            OracleStatus.FAIL,
            {"claims_observed": False},
            "attempt budget did not accept the duplicate delivery scenario",
        )
    passed = all(observed.values())
    reason = (
        "duplicate delivery shared one attempt and fenced the takeover"
        if passed
        else "duplicate delivery consumed or failed to fence an attempt"
    )
    status = OracleStatus.PASS if passed else OracleStatus.FAIL
    return build_result(oracle_id, status, observed, reason)


def outbox_dlt_ack_gating_oracle(
    adapter: DeadLetterAdapter | None,
    publisher: Any | None,
) -> OracleResult:
    """Prove a DLT source offset needs a positive broker acknowledgement."""
    oracle_id = _OUTBOX_ORACLE_ID
    if adapter is None or publisher is None:
        return blocked(oracle_id, _MISSING_DEAD_LETTER_EVIDENCE)
    try:
        published = adapter.publish(publisher)
    except AdapterUnavailableError:
        return blocked(oracle_id, "dead-letter adapter is unavailable")
    except Exception:
        observed = {_PUBLICATION_OBSERVED: False}
        return build_result(
            oracle_id,
            OracleStatus.FAIL,
            observed,
            "dead-letter publication did not return an acknowledgement",
        )
    if bool(getattr(published, _ACKNOWLEDGED, False)):
        return _commit_acknowledged(adapter, published)
    return _commit_unacknowledged(adapter, published)


def _has_capability_evidence(
    adapter: ArtifactCapabilityAdapter | None,
    token: str | None,
    details: Mapping[str, Any],
) -> bool:
    if adapter is None or token is None:
        return False
    return all(details.get(field) is not None for field in _REQUIRED_CAPABILITY_FIELDS)


def _shared_attempt_observation(
    adapter: AttemptBudgetAdapter,
    worker_id: str,
    takeover_worker_id: str,
    delivery_id: str,
) -> dict[str, bool]:
    first_state, first_lease = adapter.claim(worker_id, delivery_id=delivery_id)
    second_state, second_lease = adapter.claim(
        takeover_worker_id,
        delivery_id=delivery_id,
        budget=first_state,
    )
    return {
        "claims_observed": True,
        "one_attempt_used": getattr(second_state, "attempts_used", None) == 1,
        "same_delivery": (
            getattr(first_lease, "delivery_id", None)
            == getattr(second_lease, "delivery_id", None)
        ),
        "fencing_advanced": (
            getattr(second_lease, "fencing_token", 0)
            > getattr(first_lease, "fencing_token", 0)
        ),
    }


def _commit_unacknowledged(
    adapter: DeadLetterAdapter,
    published: Any,
) -> OracleResult:
    try:
        adapter.commit_source_offset(published)
    except AdapterUnavailableError:
        return blocked(_OUTBOX_ORACLE_ID, "dead-letter commit is unavailable")
    except Exception as error:
        commit_blocked = is_ack_gate_error(error)
        observed = {
            _PUBLICATION_OBSERVED: True,
            _ACKNOWLEDGED: False,
            _OFFSET_COMMIT_BLOCKED: commit_blocked,
        }
        status = OracleStatus.PASS if commit_blocked else OracleStatus.FAIL
        reason = (
            "unacknowledged dead-letter publication remained pending"
            if commit_blocked
            else "dead-letter commit failed for an unexpected reason"
        )
        return build_result(_OUTBOX_ORACLE_ID, status, observed, reason)
    observed = {
        _PUBLICATION_OBSERVED: True,
        _ACKNOWLEDGED: False,
        _OFFSET_COMMIT_BLOCKED: False,
    }
    return build_result(
        _OUTBOX_ORACLE_ID,
        OracleStatus.FAIL,
        observed,
        "unacknowledged dead-letter publication allowed offset commit",
    )


def _commit_acknowledged(
    adapter: DeadLetterAdapter,
    published: Any,
) -> OracleResult:
    try:
        committed = adapter.commit_source_offset(published)
    except AdapterUnavailableError:
        return blocked(_OUTBOX_ORACLE_ID, "dead-letter commit is unavailable")
    except Exception:
        observed = {
            _PUBLICATION_OBSERVED: True,
            _ACKNOWLEDGED: True,
            _OFFSET_COMMIT_ALLOWED: False,
        }
        return build_result(
            _OUTBOX_ORACLE_ID,
            OracleStatus.FAIL,
            observed,
            "acknowledged dead-letter publication could not commit offset",
        )
    offset_committed = bool(
        getattr(committed, "source_offset_committed", False)
    )
    observed = {
        _PUBLICATION_OBSERVED: True,
        _ACKNOWLEDGED: True,
        _OFFSET_COMMIT_ALLOWED: offset_committed,
    }
    status = OracleStatus.PASS if offset_committed else OracleStatus.FAIL
    reason = (
        "acknowledged dead-letter publication allowed offset commit"
        if offset_committed
        else "acknowledged dead-letter publication did not commit offset"
    )
    return build_result(_OUTBOX_ORACLE_ID, status, observed, reason)
