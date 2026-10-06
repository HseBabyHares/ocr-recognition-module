"""Fixtures and adapters shared by recognition oracle scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from sird_recognition.contracts import stages
from sird_recognition.contracts.text_observation import TextObservation
from sird_recognition.runtime import RecognizerRuntime

from sird_verification.adapters import RuntimeAdapter

_FORM_ID = "form-a"
REQUEST = MappingProxyType(
    {
        "task_id": "task-1",
        "request_id": "request-1",
        "artifact_capability": "opaque-capability",
        "limits": {"pages": 2},
        "policy_ref": "policy-1",
    },
)
CONTEXT = stages.StageContext(
    contract_version="v1",
    request_id="request-1",
    attempt_id="attempt-1",
    artifact_capability="opaque-capability",
    limits={"pages": 2},
    policy_ref="policy-1",
)
_DOCUMENT = stages.PreparedDocument(
    pages=(
        stages.PreparedPage(
            page_id="page-1",
            source_id="source-1",
            status="prepared",
            checksum="sha256:page",
            metadata={},
        ),
    ),
    preparation_complete=True,
    diagnostics=(),
)
_SPEC = stages.ExecutionSpec(
    form_id=_FORM_ID,
    profile_id="profile-a",
    stage_names=("extract",),
    implementation_checksums={"extract": "sha256:stage"},
    calibration_ref="calibration-a",
)


@dataclass
class StagePorts:
    """One deterministic implementation of every runtime stage port."""

    candidate_ids: tuple[str, ...]
    specification: stages.ExecutionSpec | None
    execution_result: stages.ExecutionResult

    def prepare(
        self,
        context: stages.StageContext,
    ) -> stages.PreparedDocument:
        return _DOCUMENT

    def probe(
        self,
        document: stages.PreparedDocument,
        context: stages.StageContext,
    ) -> stages.ProbeResult:
        return stages.ProbeResult(
            search_result="bounded search",
            analysis_complete=True,
            candidate_ids=self.candidate_ids,
            evidence_refs=("evidence-1",),
        )

    def resolve(
        self,
        probe: stages.ProbeResult,
        context: stages.StageContext,
    ) -> stages.FormResolutionDecision:
        if self.specification is None:
            return stages.UnresolvedForm()
        return stages.ResolvedForm(self.specification)

    def execute(
        self,
        document: stages.PreparedDocument,
        specification: stages.ExecutionSpec,
        context: stages.StageContext,
        *,
        observations: tuple[TextObservation, ...] = (),
    ) -> stages.ExecutionResult:
        return self.execution_result


class AcceptingAdapter:
    """Adapter that accepts any selector payload."""

    def parse_request(
        self,
        request_payload: dict[str, object],
    ) -> dict[str, object]:
        return request_payload


def adapter(
    candidates: tuple[str, ...],
    *,
    specification: stages.ExecutionSpec | None = _SPEC,
    execution: stages.ExecutionResult | None = None,
) -> RuntimeAdapter:
    """Build a runtime adapter with deterministic stage responses."""
    execution_result = execution or stages.ExecutionResult(
        fields={
            "known": stages.FieldResult(
                stages.FieldStatus.EXTRACTED,
                "value",
            ),
        },
        evidence_refs=("field-evidence",),
        diagnostics=(),
        complete=True,
    )
    stage_ports = StagePorts(candidates, specification, execution_result)
    runtime = RecognizerRuntime(
        stage_ports,
        stage_ports,
        stage_ports,
        stage_ports,
    )
    return RuntimeAdapter(runtime)
