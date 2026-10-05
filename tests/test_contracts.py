from typing import Final

from sird_recognition.contracts import stages

MAX_PAGES: Final = 1
PAGE_WIDTH: Final = 100
PAGE_HEIGHT: Final = 200

AmbiguousForm = stages.AmbiguousForm
ExecutionResult = stages.ExecutionResult
ExecutionSpec = stages.ExecutionSpec
FieldResult = stages.FieldResult
FieldStatus = stages.FieldStatus
PreparedDocument = stages.PreparedDocument
PreparedPage = stages.PreparedPage
ProbeResult = stages.ProbeResult
ResolvedForm = stages.ResolvedForm
StageContext = stages.StageContext
UnresolvedForm = stages.UnresolvedForm
UnsupportedForm = stages.UnsupportedForm


def test_context_keeps_capability() -> None:
    context = StageContext(
        contract_version="sird.ocr.v1",
        request_id="request-1",
        attempt_id="attempt-1",
        artifact_capability="signed-capability",
        limits={"max_pages": MAX_PAGES},
        policy_ref="policy-v1",
    )

    assert context.artifact_capability == "signed-capability"


def test_page_keeps_checksum() -> None:
    page = PreparedPage(
        page_id="page-1",
        source_id="source-1",
        status="prepared",
        checksum="sha256:page",
        metadata={"width": PAGE_WIDTH, "height": PAGE_HEIGHT},
    )

    assert page.checksum == "sha256:page"


def test_document_keeps_completeness() -> None:
    page = PreparedPage("page-1", "source-1", "prepared", "sha256:page", {})
    document = PreparedDocument((page,), True, ())

    assert document.preparation_complete is True


def test_probe_keeps_candidate() -> None:
    probe = ProbeResult("detected", True, ("candidate-1",), ("evidence-1",))

    assert probe.candidate_ids == ("candidate-1",)


def test_spec_keeps_form() -> None:
    specification = ExecutionSpec(
        "snils_card",
        "snils-default",
        ("read", "extract", "validate"),
        {"reader": "sha256:reader"},
        "calibration-v1",
    )

    assert specification.form_id == "snils_card"


def test_form_resolution_decisions_are_explicit() -> None:
    specification = ExecutionSpec(
        "snils_card",
        "snils-default",
        ("read",),
        {"reader": "sha256:reader"},
        "calibration-v1",
    )

    assert ResolvedForm(specification).specification is specification
    assert AmbiguousForm(("form-a", "form-b")).alternatives == (
        "form-a",
        "form-b",
    )
    assert UnsupportedForm("form-x").form_id == "form-x"
    assert isinstance(UnresolvedForm(), UnresolvedForm)


def test_execution_keeps_completeness() -> None:
    execution = ExecutionResult(
        {"snils": FieldResult(FieldStatus.EXTRACTED, "observed")},
        ("evidence-1",),
        (),
        True,
    )

    assert execution.complete is True
