"""Stage ports that run the SNILS card profile inside ``RecognizerRuntime``.

Prepare verifies the artifact capability, Probe and Resolve select the
single supported form, and Execute reads the bound bytes and maps the
``SnilsRecognitionService`` result to field outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from sird_recognition._runtime_request import RecognitionError
from sird_recognition.artifact_capability import CapabilityVerifier
from sird_recognition.codes import TechnicalCode
from sird_recognition.contracts import stages
from sird_recognition.contracts.ports import MaterialReaderPort
from sird_recognition.contracts.text_observation import TextObservation
from sird_recognition.snils_recognition import SnilsRecognitionService

SNILS_FORM_ID = "snils_card"
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


class WholePageProbe:
    """Treat every prepared page as one SNILS card candidate."""

    # shortcut: no form classifier; each page is one candidate. Replace
    # with a detector when a second form or multi-card input is supported.
    def probe(
        self, document: stages.PreparedDocument, context: stages.StageContext
    ) -> stages.ProbeResult:
        return stages.ProbeResult(
            search_result="whole_page",
            analysis_complete=True,
            candidate_ids=tuple(page.page_id for page in document.pages),
            evidence_refs=(),
        )


@dataclass(frozen=True, slots=True)
class FixedFormResolve:
    """Resolve the single supported form to its execution specification."""

    specification: stages.ExecutionSpec

    def resolve(
        self, probe: stages.ProbeResult, context: stages.StageContext
    ) -> stages.FormResolutionDecision:
        return stages.ResolvedForm(self.specification)


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
        page = document.pages[0]
        if page.prepared_artifact is None:
            raise RecognitionError(TechnicalCode.MATERIAL_UNAVAILABLE)
        image = self.reader.read(
            page.prepared_artifact, expected_checksum=page.checksum
        )
        recognized = self.service.recognize_image(
            image,
            timeout_seconds=float(context.limits["timeout_seconds"]),
            language=specification.reader_language or "rus+eng",
            request_id=context.request_id,
            attempt_id=context.attempt_id,
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
