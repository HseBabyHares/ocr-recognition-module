"""Public facade for focused executable verification oracles."""

from __future__ import annotations

from sird_verification._architecture_oracle import architecture_boundary_oracle
from sird_verification._oracle_support import (
    blocked,
    build_result,
    enum_value,
    imported_modules,
    is_ack_gate_error,
    is_capability_rejection,
    resolve_recognition_root,
)
from sird_verification._recognition_oracles import (
    multiple_candidate_refusal_oracle,
    no_candidate_refusal_oracle,
    no_guessing_oracle,
    partial_field_preservation_oracle,
    strict_selector_rejection_oracle,
)
from sird_verification._recognition_support import (
    candidate_observed,
    has_partial_evidence,
    no_guessing_observed,
    parse_request,
    partial_observed,
    recognize,
)
from sird_verification._workflow_oracles import (
    artifact_capability_rejection_oracle,
    outbox_dlt_ack_gating_oracle,
    shared_attempt_budget_oracle,
)


oracle_strict_selector_rejection = strict_selector_rejection_oracle
oracle_no_candidate_refusal = no_candidate_refusal_oracle
oracle_multiple_candidate_refusal = multiple_candidate_refusal_oracle
oracle_partial_field_preservation = partial_field_preservation_oracle
oracle_no_guessing = no_guessing_oracle
oracle_artifact_capability_rejection = artifact_capability_rejection_oracle
oracle_shared_attempt_budget = shared_attempt_budget_oracle
oracle_outbox_dlt_ack_gating = outbox_dlt_ack_gating_oracle
oracle_architecture_boundary = architecture_boundary_oracle
