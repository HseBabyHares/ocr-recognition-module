from __future__ import annotations

from sird_recognition.contracts.stages import (
    ExecutionResult,
    FieldResult,
    FieldStatus,
)

from sird_verification.contracts import OracleStatus
from sird_verification.oracles import (
    multiple_candidate_refusal_oracle,
    no_candidate_refusal_oracle,
    no_guessing_oracle,
    partial_field_preservation_oracle,
    strict_selector_rejection_oracle,
)
from _recognition_oracle_support import (
    CONTEXT,
    REQUEST,
    AcceptingAdapter,
    adapter,
    _FORM_ID,
)

def test_selector_rejection() -> None:
    selected = {**REQUEST, "form_id": "forbidden-selector"}

    passed = strict_selector_rejection_oracle(
        adapter((_FORM_ID,)),
        selected,
    )
    failed = strict_selector_rejection_oracle(
        AcceptingAdapter(),
        selected,
    )
    blocked = strict_selector_rejection_oracle(None, selected)

    assert passed.status is OracleStatus.PASS
    assert passed.observed == {"rejected": True}
    assert failed.status is OracleStatus.FAIL
    assert blocked.status is OracleStatus.BLOCKED


def test_candidate_refusal() -> None:
    none = no_candidate_refusal_oracle(adapter(()), REQUEST, CONTEXT)
    many = multiple_candidate_refusal_oracle(
        adapter((_FORM_ID, "form-b")),
        REQUEST,
        CONTEXT,
    )
    wrong = no_candidate_refusal_oracle(
        adapter((_FORM_ID,)),
        REQUEST,
        CONTEXT,
    )

    assert none.status is OracleStatus.PASS
    assert many.status is OracleStatus.PASS
    assert wrong.status is OracleStatus.FAIL
    assert none.observed["fields_empty"] is True
    assert many.observed["multiple_candidates"] is True


def test_partial_fields() -> None:
    fields = {
        "name": FieldResult(FieldStatus.EXTRACTED, "read"),
        "amount": FieldResult(FieldStatus.UNREADABLE, None),
    }
    test_adapter = adapter(
        (_FORM_ID,),
        execution=ExecutionResult(
            fields=fields,
            evidence_refs=("field-evidence",),
            diagnostics=("amount_unreadable",),
            complete=False,
        ),
    )

    passed = partial_field_preservation_oracle(
        test_adapter,
        REQUEST,
        CONTEXT,
        fields,
    )
    failed = partial_field_preservation_oracle(
        test_adapter,
        REQUEST,
        CONTEXT,
        {"name": FieldResult(FieldStatus.EXTRACTED, "changed")},
    )
    blocked = partial_field_preservation_oracle(
        test_adapter,
        REQUEST,
        CONTEXT,
        None,
    )

    assert passed.status is OracleStatus.PASS
    assert failed.status is OracleStatus.FAIL
    assert blocked.status is OracleStatus.BLOCKED


def test_no_guessing() -> None:
    passed = no_guessing_oracle(
        adapter((_FORM_ID,), specification=None),
        REQUEST,
        CONTEXT,
    )
    failed = no_guessing_oracle(adapter((_FORM_ID,)), REQUEST, CONTEXT)
    blocked = no_guessing_oracle(None, REQUEST, CONTEXT)

    assert passed.status is OracleStatus.PASS
    assert passed.observed["fields_empty"] is True
    assert failed.status is OracleStatus.FAIL
    assert blocked.status is OracleStatus.BLOCKED
