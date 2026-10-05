from dataclasses import FrozenInstanceError
from unittest.mock import Mock

import pytest

from sird_recognition.contracts import stages as stage_contracts
from sird_recognition.runtime import (
    RecognitionResponse,
    RecognizeRequest,
    RecognizerRuntime,
)

TARGET_FIELD = "target"
COMPLETE = "complete"
PARTIAL = "partial"
_VALUE_ATTRIBUTE = "value"


class TestFieldResultValidation:
    @pytest.mark.parametrize(
        ("status", "field_value"),
        [
            (stage_contracts.FieldStatus.EXTRACTED, "observed"),
            (stage_contracts.FieldStatus.ABSENT, None),
            (stage_contracts.FieldStatus.UNREADABLE, None),
            (stage_contracts.FieldStatus.CONFLICT, None),
            (stage_contracts.FieldStatus.NOT_APPLICABLE, None),
            (stage_contracts.FieldStatus.NOT_PROCESSED, None),
        ],
    )
    def test_each_field_status_is_explicit(
        self, status: stage_contracts.FieldStatus, field_value: object | None
    ) -> None:
        field_result = stage_contracts.FieldResult(
            status=status,
            value=field_value,
            validations=("format_invalid",),
            evidence_refs=("evidence-1",),
            diagnostics=("diagnostic-1",),
        )

        assert (
            field_result.status,
            getattr(field_result, _VALUE_ATTRIBUTE),
            field_result.validations,
            field_result.evidence_refs,
            field_result.diagnostics,
            field_result.required,
        ) == (
            status,
            field_value,
            ("format_invalid",),
            ("evidence-1",),
            ("diagnostic-1",),
            True,
        )

    def test_field_result_rejects_unknown_status(self) -> None:
        with pytest.raises(ValueError, match="unknown field status"):
            stage_contracts.FieldResult("future_status", None)  # type: ignore

    def test_not_applicable_tracks_required_flag(self) -> None:
        field_result = stage_contracts.FieldResult(
            stage_contracts.FieldStatus.NOT_APPLICABLE, None, required=False
        )

        assert field_result.required is False


class FieldResultFactory:
    @classmethod
    def context(cls) -> stage_contracts.StageContext:
        return stage_contracts.StageContext(
            contract_version="sird.ocr.v1",
            request_id="request-1",
            attempt_id="attempt-1",
            artifact_capability="capability-1",
            limits={"max_pages": 1},
            policy_ref="policy-1",
        )

    @classmethod
    def request(cls) -> RecognizeRequest:
        return RecognizeRequest(
            task_id="task-1",
            request_id="request-1",
            artifact_capability="capability-1",
            limits={"max_pages": 1},
            policy_ref="policy-1",
        )

    @classmethod
    def prepared(cls) -> stage_contracts.PreparedDocument:
        return stage_contracts.PreparedDocument(
            pages=(
                stage_contracts.PreparedPage(
                    "page-1", "source-1", "prepared", "sha256:page", {}
                ),
            ),
            preparation_complete=True,
            diagnostics=(),
        )

    @classmethod
    def specification(cls) -> stage_contracts.ExecutionSpec:
        return stage_contracts.ExecutionSpec(
            "snils_card",
            "snils-default",
            ("extract",),
            {"reader": "sha256:reader"},
            "calibration-1",
        )

    @classmethod
    def stage(cls, method_name: str, stage_result: object) -> Mock:
        stage_mock = Mock()
        getattr(stage_mock, method_name).return_value = stage_result
        return stage_mock

    @classmethod
    def typed_response(
        cls, fields: dict[str, stage_contracts.FieldResult]
    ) -> RecognitionResponse:
        context = FieldResultFactory.context()
        request = FieldResultFactory.request()
        runtime = RecognizerRuntime(
            FieldResultFactory.stage("prepare", FieldResultFactory.prepared()),
            FieldResultFactory.stage(
                "probe",
                stage_contracts.ProbeResult(
                    "detected", True, ("candidate-1",), ()
                ),
            ),
            FieldResultFactory.stage(
                "resolve",
                stage_contracts.ResolvedForm(
                    FieldResultFactory.specification()
                ),
            ),
            FieldResultFactory.stage(
                "execute",
                stage_contracts.ExecutionResult(fields, (), (), True),
            ),
        )
        return runtime.recognize(request, context)


@pytest.mark.parametrize(
    ("fields", "expected_completeness"),
    [
        (
            {
                TARGET_FIELD: stage_contracts.FieldResult(
                    stage_contracts.FieldStatus.EXTRACTED, "observed"
                )
            },
            COMPLETE,
        ),
        (
            {
                TARGET_FIELD: stage_contracts.FieldResult(
                    stage_contracts.FieldStatus.ABSENT, None
                )
            },
            PARTIAL,
        ),
        (
            {
                TARGET_FIELD: stage_contracts.FieldResult(
                    stage_contracts.FieldStatus.UNREADABLE, None
                )
            },
            PARTIAL,
        ),
        (
            {
                TARGET_FIELD: stage_contracts.FieldResult(
                    stage_contracts.FieldStatus.CONFLICT, None
                )
            },
            PARTIAL,
        ),
        (
            {
                TARGET_FIELD: stage_contracts.FieldResult(
                    stage_contracts.FieldStatus.NOT_APPLICABLE, None
                )
            },
            PARTIAL,
        ),
        (
            {
                TARGET_FIELD: stage_contracts.FieldResult(
                    stage_contracts.FieldStatus.NOT_APPLICABLE,
                    None,
                    required=False,
                )
            },
            COMPLETE,
        ),
        (
            {
                TARGET_FIELD: stage_contracts.FieldResult(
                    stage_contracts.FieldStatus.NOT_PROCESSED, None
                )
            },
            PARTIAL,
        ),
        ({}, PARTIAL),
    ],
    ids=(
        "extracted",
        "absent",
        "unreadable",
        "conflict",
        "required-not-applicable",
        "optional-not-applicable",
        "not-processed",
        "empty",
    ),
)
def test_typed_fields_preserve_completeness(
    fields: dict[str, stage_contracts.FieldResult], expected_completeness: str
) -> None:
    response = FieldResultFactory.typed_response(fields)

    assert response.fields == fields
    completeness = response.result_completeness
    assert completeness is not None
    assert completeness.value == expected_completeness


def test_execution_result_has_only_typed_fields() -> None:
    execution_result = stage_contracts.ExecutionResult({}, (), (), True)

    assert execution_result.fields == {}
    assert not hasattr(execution_result, "field_results")


def test_field_result_rejects_implicit_values() -> None:
    with pytest.raises(ValueError, match="require a value"):
        stage_contracts.FieldResult(
            stage_contracts.FieldStatus.EXTRACTED, None
        )

    with pytest.raises(ValueError, match="require a null value"):
        stage_contracts.FieldResult(
            stage_contracts.FieldStatus.UNREADABLE, "maybe-observed"
        )


def test_field_result_is_immutable() -> None:
    field_result = stage_contracts.FieldResult(
        stage_contracts.FieldStatus.ABSENT, None
    )

    with pytest.raises(FrozenInstanceError):
        field_result.status = stage_contracts.FieldStatus.EXTRACTED  # type: ignore
