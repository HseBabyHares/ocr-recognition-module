"""Stage ports that run the SNILS card profile inside ``RecognizerRuntime``.

Prepare verifies the artifact capability, Probe reads the page text once,
Resolve classifies it among the supported forms, and Execute maps the
``SnilsRecognitionService`` result for those observations to field outcomes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from sird_recognition._runtime_request import RecognitionError
from sird_recognition.artifact_capability import CapabilityVerifier
from sird_recognition.codes import TechnicalCode
from sird_recognition.contracts import stages
from sird_recognition.contracts.ports import MaterialReaderPort
from sird_recognition.contracts.text_observation import TextObservation
from sird_recognition.form_classifier import classify_form
from sird_recognition.snils_recognition import (
    SnilsRecognitionResult,
    SnilsRecognitionService,
)

_SNILS_VALIDATION = MappingProxyType(
    {
        "rule_id": "snils_checksum",
        "rule_version": "1",
        "reason": "checksum_valid",
        "status": "valid",
    }
)


@dataclass(frozen=True, slots=True)
class CapabilityPrepare:
    """Accept only material that a valid capability binds to this task."""

    verifier: CapabilityVerifier
    policy_ref: str | None = None

    def prepare(self, context: stages.StageContext) -> stages.PreparedDocument:
        if (
            self.policy_ref is not None
            and context.policy_ref != self.policy_ref
        ):
            raise RecognitionError(TechnicalCode.INVALID_CONFIGURATION)
        claims = self.verifier.verify(
            context.artifact_capability,
            task_id=context.task_id,
            request_id=context.request_id,
        )
        max_bytes = context.limits.get("max_input_bytes")
        if max_bytes is not None and claims.size > max_bytes:
            raise RecognitionError(TechnicalCode.INPUT_LIMIT_EXCEEDED)
        page = stages.PreparedPage(
            page_id="page-1",
            source_id=claims.object_id,
            status="prepared",
            checksum=claims.checksum,
            metadata={
                "media_type": claims.media_type,
                "size": claims.size,
                "generation": claims.generation,
            },
            prepared_artifact=claims.object_key,
            page_index=0,
        )
        return stages.PreparedDocument(
            pages=(page,), preparation_complete=True, diagnostics=()
        )


@dataclass(frozen=True, slots=True)
class TextFormProbe:
    """Read the bound page text once for the form classifier."""

    service: SnilsRecognitionService
    reader: MaterialReaderPort

    def probe(
        self, document: stages.PreparedDocument, context: stages.StageContext
    ) -> stages.ProbeResult:
        page = document.pages[0]
        if page.prepared_artifact is None:
            raise RecognitionError(TechnicalCode.MATERIAL_UNAVAILABLE)
        image = self.reader.read(
            page.prepared_artifact, expected_checksum=page.checksum
        )
        try:
            observations = self.service.read_page(
                image, timeout_seconds=float(context.limits["timeout_seconds"])
            )
        except ValueError as error:
            raise RecognitionError(TechnicalCode.INVALID_INPUT) from error
        # No text at all is an incomplete analysis, not a subject conclusion.
        return stages.ProbeResult(
            search_result="detected" if observations else "uncertain",
            analysis_complete=bool(observations),
            candidate_ids=(page.page_id,),
            evidence_refs=(),
            observations=observations,
        )


@dataclass(frozen=True, slots=True)
class MarkerFormResolve:
    """Resolve the classified form to its execution specification."""

    specifications: Mapping[str, stages.ExecutionSpec]

    def resolve(
        self, probe: stages.ProbeResult, context: stages.StageContext
    ) -> stages.FormResolutionDecision:
        decision = classify_form(
            observation.raw_text for observation in probe.observations
        )
        if not isinstance(decision, str):
            return decision
        specification = self.specifications.get(decision)
        if specification is None:
            return stages.UnsupportedForm(decision)
        return stages.ResolvedForm(specification)


@dataclass(frozen=True, slots=True)
class SnilsExecuteProfile:
    """Read the bound bytes and run the local SNILS recognizer."""

    service: SnilsRecognitionService
    reader: MaterialReaderPort

    def execute(
        self,
        document: stages.PreparedDocument,
        specification: stages.ExecutionSpec,
        context: stages.StageContext,
        *,
        observations: tuple[TextObservation, ...] = (),
    ) -> stages.ExecutionResult:
        if observations:
            recognized = self.service.recognize_observations(
                observations,
                request_id=context.request_id,
                attempt_id=context.attempt_id,
            )
        else:
            recognized = self._recognize_material(
                document, specification, context
            )
        verified = recognized.verified
        return stages.ExecutionResult(
            fields={
                "snils": _field(
                    recognized.snils_number if verified else None,
                    (_SNILS_VALIDATION,),
                ),
                "full_name": _field(
                    recognized.full_name if verified else None
                ),
                "birth_date": _field(
                    recognized.birth_date if verified else None
                ),
            },
            evidence_refs=(),
            # The contract has no severity, so a pass already sent as a
            # field validation must not also appear as a diagnostic.
            diagnostics=tuple(
                code
                for code in recognized.diagnostics
                if code != "snils_checksum_valid"
            ),
            complete=True,
            execution_metadata={
                "variant_count": recognized.variant_count,
                "observation_count": recognized.observation_count,
            },
        )

    def _recognize_material(
        self,
        document: stages.PreparedDocument,
        specification: stages.ExecutionSpec,
        context: stages.StageContext,
    ) -> SnilsRecognitionResult:
        page = document.pages[0]
        if page.prepared_artifact is None:
            raise RecognitionError(TechnicalCode.MATERIAL_UNAVAILABLE)
        image = self.reader.read(
            page.prepared_artifact, expected_checksum=page.checksum
        )
        return self.service.recognize_image(
            image,
            timeout_seconds=float(context.limits["timeout_seconds"]),
            language=specification.reader_language or "rus+eng",
            request_id=context.request_id,
            attempt_id=context.attempt_id,
        )


def _field(
    text: str | None, validations: tuple[object, ...] = ()
) -> stages.FieldResult:
    if text is None:
        return stages.FieldResult(stages.FieldStatus.UNREADABLE, required=True)
    return stages.FieldResult(
        stages.FieldStatus.EXTRACTED,
        text,
        validations=validations,
        required=True,
    )
