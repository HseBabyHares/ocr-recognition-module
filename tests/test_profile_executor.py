from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace

import pytest

from sird_recognition.codes import TechnicalCode
from sird_recognition.contracts import stages as stage_contracts
from sird_recognition.contracts.text_observation import (
    AdapterDescriptor,
    TextObservation,
)
from sird_recognition.profile_executor import ReaderAwareExecuteProfile
from sird_recognition.runtime import RecognitionError
from sird_recognition.text_reader_errors import (
    TextReaderExecutionError,
    TextReaderLimitError,
    TextReaderUnavailableError,
)

_DEFAULT_TIMEOUT = 5
_ZERO = 0
_ONE = 1
_DEFAULT_READER_ID = "vlm"
_READER_CHECKSUM = "sha256:reader"
_LANGUAGE = "rus+eng"


_DEFAULT_DESCRIPTOR = object()
_ARTIFACT_REF = "artifact"
_RASTER = b"raster"
_SOURCE_FILE = "source-file"
_PREPARED = "prepared"


class ProfileCase:
    @classmethod
    def spec(
        cls,
        reader_id: str = _DEFAULT_READER_ID,
        *,
        model_revisions: dict[str, str] | None = None,
        stage_names: tuple[str, ...] = ("read", "extract"),
        language: str | None = _LANGUAGE,
        cpu_threads: int = _ONE,
    ) -> stage_contracts.ExecutionSpec:
        revisions = (
            {reader_id: "model-v1"}
            if model_revisions is None
            else model_revisions
        )
        return stage_contracts.ExecutionSpec(
            "snils_card",
            "snils-vlm",
            stage_names,
            {reader_id: _READER_CHECKSUM},
            "calibration-1",
            reader_language=language,
            reader_cpu_threads=cpu_threads,
            reader_order=(reader_id,),
            reader_model_revisions=revisions,
        )

    @classmethod
    def context(
        cls,
        timeout_seconds: int | None = _DEFAULT_TIMEOUT,
    ) -> stage_contracts.StageContext:
        limits = (
            {}
            if timeout_seconds is None
            else {"timeout_seconds": timeout_seconds}
        )
        return stage_contracts.StageContext(
            "sird.ocr.v1",
            "request-1",
            "attempt-1",
            "capability-1",
            limits,
            "policy-1",
        )

    @classmethod
    def observation(
        cls,
        reader_id: str = _DEFAULT_READER_ID,
        *,
        language: str | None = _LANGUAGE,
        descriptor: AdapterDescriptor | None | object = _DEFAULT_DESCRIPTOR,
    ) -> TextObservation:
        if descriptor is _DEFAULT_DESCRIPTOR:
            descriptor = AdapterDescriptor(
                adapter_id=reader_id,
                adapter_version="reader-v1",
                implementation_checksum=_READER_CHECKSUM,
                model_revision="model-v1",
                device="cpu",
                input_kinds=("raster_bytes",),
                output_capabilities=frozenset(("text",)),
                configuration={"language": _LANGUAGE},
            )
        assert descriptor is None or isinstance(descriptor, AdapterDescriptor)
        return TextObservation(
            "observed",
            reader_id,
            "reader-v1",
            descriptor=descriptor,
            language=language,
        )

    @classmethod
    def profile(
        cls,
        chain: RecordingReaderChain | None = None,
        material: RecordingMaterialReader | None = None,
    ) -> tuple[ReaderAwareExecuteProfile, RecordingDelegate]:
        chain = chain or RecordingReaderChain()
        material = material or RecordingMaterialReader(
            {_ARTIFACT_REF: _RASTER}
        )
        delegate = RecordingDelegate()
        return ReaderAwareExecuteProfile(delegate, chain, material), delegate

    @classmethod
    def document(
        cls,
        *pages: stage_contracts.PreparedPage,
        complete: bool = True,
    ) -> stage_contracts.PreparedDocument:
        return stage_contracts.PreparedDocument(tuple(pages), complete, ())

    @classmethod
    def execute(
        cls,
        profile_instance: ReaderAwareExecuteProfile,
        *,
        page: stage_contracts.PreparedPage | None = None,
        specification: stage_contracts.ExecutionSpec | None = None,
        context: stage_contracts.StageContext | None = None,
    ) -> None:
        profile_instance.execute(
            cls.document(page or cls.prepared_page()),
            specification or cls.spec(),
            context or cls.context(),
        )

    @classmethod
    def prepared_page(
        cls,
        artifact_ref: str = _ARTIFACT_REF,
        raster: bytes = _RASTER,
        page_id: str = "page",
    ) -> stage_contracts.PreparedPage:
        checksum = hashlib.sha256(raster).hexdigest()
        return stage_contracts.PreparedPage(
            page_id,
            _SOURCE_FILE,
            _PREPARED,
            f"sha256:{checksum}",
            {},
            artifact_ref,
        )


class RecordingMaterialReader:
    def __init__(self, materials: dict[str, bytes]) -> None:
        self.materials = materials
        self.calls: list[tuple[str, str]] = []

    def read(self, artifact_ref: str, *, expected_checksum: str) -> bytes:
        self.calls.append((artifact_ref, expected_checksum))
        material = self.materials[artifact_ref]
        material_checksum = hashlib.sha256(material).hexdigest()
        if f"sha256:{material_checksum}" != expected_checksum:
            raise ValueError("material checksum mismatch")
        return material


class RecordingReaderChain:
    def __init__(
        self,
        reader_id: str = _DEFAULT_READER_ID,
        *,
        error: Exception | None = None,
        observation: TextObservation | None = None,
    ) -> None:
        self.reader_id = reader_id
        self.error = error
        self.observation = observation
        self.images: list[bytes] = []

    @property
    def reader_ids(self) -> tuple[str, ...]:
        return (self.reader_id,)

    def read(
        self,
        image: bytes,
        *,
        timeout_seconds: float,
        language: str,
        cpu_threads: int,
    ) -> TextObservation:
        assert timeout_seconds > _ZERO
        assert language == _LANGUAGE
        assert cpu_threads == _ONE
        self.images.append(image)
        if self.error is not None:
            raise self.error
        return self.observation or ProfileCase.observation(self.reader_id)


@dataclass
class RecordingDelegate:
    observations: tuple[TextObservation, ...] = ()
    document: stage_contracts.PreparedDocument | None = None
    calls: int = 0

    def execute(
        self,
        document: stage_contracts.PreparedDocument,
        specification: stage_contracts.ExecutionSpec,
        context: stage_contracts.StageContext,
        *,
        observations: tuple[TextObservation, ...] = (),
    ) -> stage_contracts.ExecutionResult:
        self.calls += 1
        self.document = document
        self.observations = observations
        return stage_contracts.ExecutionResult({}, (), (), True)


class TestProfileReader:
    def test_timeout_mapping(self) -> None:
        profile, _ = ProfileCase.profile(
            RecordingReaderChain(error=TextReaderLimitError("timeout"))
        )

        with pytest.raises(RecognitionError) as raised_error:
            ProfileCase.execute(profile)

        assert (
            raised_error.value.code is TechnicalCode.EXECUTION_LIMIT_EXCEEDED
        )

    @pytest.mark.parametrize(
        ("reader_error", "expected"),
        (
            (
                TextReaderUnavailableError("missing model"),
                TechnicalCode.MODEL_UNAVAILABLE,
            ),
            (
                TextReaderExecutionError("reader failed"),
                TechnicalCode.EXECUTION_ERROR,
            ),
        ),
    )
    def test_reader_failures(
        self,
        reader_error: Exception,
        expected: TechnicalCode,
    ) -> None:
        profile, _ = ProfileCase.profile(
            RecordingReaderChain(error=reader_error)
        )

        with pytest.raises(RecognitionError) as raised_error:
            ProfileCase.execute(profile)
        assert raised_error.value.code is expected

    def test_failed_pages_are_skipped(self) -> None:
        chain = RecordingReaderChain()
        profile, delegate = ProfileCase.profile(
            chain,
            RecordingMaterialReader(
                {
                    "first-artifact": b"first-raster",
                    "second-artifact": b"second-raster",
                }
            ),
        )

        profile.execute(
            ProfileCase.document(
                stage_contracts.PreparedPage(
                    "failed", _SOURCE_FILE, "failed", "bad", {}
                ),
                ProfileCase.prepared_page(
                    "first-artifact", b"first-raster", "prepared-1"
                ),
                ProfileCase.prepared_page(
                    "second-artifact", b"second-raster", "prepared-2"
                ),
                complete=False,
            ),
            ProfileCase.spec(),
            ProfileCase.context(),
        )

        assert chain.images == [b"first-raster", b"second-raster"]
        assert len(delegate.observations) == 2

    def test_missing_artifact(self) -> None:
        profile, _ = ProfileCase.profile()

        with pytest.raises(RecognitionError) as raised_error:
            ProfileCase.execute(
                profile,
                page=stage_contracts.PreparedPage(
                    "page", "source", _PREPARED, "bad", {}
                ),
            )

        assert raised_error.value.code is TechnicalCode.MATERIAL_UNAVAILABLE

    def test_checksum_mismatch(self) -> None:
        profile, _ = ProfileCase.profile(
            material=RecordingMaterialReader({_ARTIFACT_REF: b"other"})
        )

        with pytest.raises(RecognitionError) as raised_error:
            ProfileCase.execute(profile)

        assert raised_error.value.code is TechnicalCode.MATERIAL_UNAVAILABLE

    def test_reader_order(self) -> None:
        profile, _ = ProfileCase.profile(RecordingReaderChain(reader_id="vlm"))

        with pytest.raises(RecognitionError) as raised_error:
            ProfileCase.execute(
                profile,
                specification=ProfileCase.spec(reader_id="tesseract"),
            )

        assert raised_error.value.code is TechnicalCode.CAPABILITY_MISMATCH


class TestProfileProvenance:
    def test_bad_implementation(self) -> None:
        observation = ProfileCase.observation()
        assert observation.descriptor is not None
        bad_descriptor = replace(
            observation.descriptor,
            implementation_checksum="sha256:wrong",
        )

        error = self._provenance_error(
            replace(observation, descriptor=bad_descriptor)
        )

        assert error.code is TechnicalCode.CAPABILITY_MISMATCH

    def test_bad_model(self) -> None:
        observation = ProfileCase.observation()
        assert observation.descriptor is not None
        bad_descriptor = replace(
            observation.descriptor,
            model_revision="model-wrong",
        )

        error = self._provenance_error(
            replace(observation, descriptor=bad_descriptor)
        )

        assert error.code is TechnicalCode.CAPABILITY_MISMATCH

    def test_bad_language(self) -> None:
        error = self._provenance_error(ProfileCase.observation(language="eng"))

        assert error.code is TechnicalCode.CAPABILITY_MISMATCH

    def test_missing_descriptor(self) -> None:
        error = self._provenance_error(
            ProfileCase.observation(descriptor=None)
        )

        assert error.code is TechnicalCode.CAPABILITY_MISMATCH

    def test_modeless_reader(self) -> None:
        observation = ProfileCase.observation("vlm")
        assert observation.descriptor is not None
        modeless_descriptor = replace(
            observation.descriptor, model_revision=None
        )
        profile, delegate = ProfileCase.profile(
            RecordingReaderChain(
                observation=replace(
                    observation, descriptor=modeless_descriptor
                )
            )
        )

        ProfileCase.execute(
            profile,
            specification=ProfileCase.spec(model_revisions={}),
        )

        assert len(delegate.observations) == _ONE

    def _provenance_error(
        self,
        observation: TextObservation,
        specification: stage_contracts.ExecutionSpec | None = None,
    ) -> RecognitionError:
        profile_instance, _ = ProfileCase.profile(
            RecordingReaderChain(observation=observation)
        )
        return pytest.raises(
            RecognitionError,
            profile_instance.execute,
            ProfileCase.document(ProfileCase.prepared_page()),
            specification or ProfileCase.spec(),
            ProfileCase.context(),
        ).value


class TestProfileConfiguration:
    @pytest.mark.parametrize("timeout_seconds", (None, _ZERO))
    def test_timeout_required(
        self,
        timeout_seconds: int | None,
    ) -> None:
        profile, _ = ProfileCase.profile()

        with pytest.raises(RecognitionError) as raised_error:
            ProfileCase.execute(
                profile,
                context=ProfileCase.context(timeout_seconds),
            )

        assert raised_error.value.code is TechnicalCode.INVALID_CONFIGURATION

    @pytest.mark.parametrize(
        ("language", "cpu_threads"),
        ((None, _ONE), ("rus+eng", _ZERO)),
    )
    def test_bad_reader_config(
        self,
        language: str | None,
        cpu_threads: int,
    ) -> None:
        profile, _ = ProfileCase.profile()

        with pytest.raises(RecognitionError) as raised_error:
            ProfileCase.execute(
                profile,
                specification=ProfileCase.spec(
                    language=language,
                    cpu_threads=cpu_threads,
                ),
            )

        assert raised_error.value.code is TechnicalCode.INVALID_CONFIGURATION

    def test_read_stage_is_required(self) -> None:
        chain = RecordingReaderChain()
        profile, delegate = ProfileCase.profile(chain)

        ProfileCase.execute(
            profile,
            specification=ProfileCase.spec(stage_names=("extract",)),
        )

        assert chain.images == []
        assert delegate.observations == ()
