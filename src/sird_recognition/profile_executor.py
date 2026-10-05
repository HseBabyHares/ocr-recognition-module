"""Profile execution adapter that owns OCR stage execution."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace

from sird_recognition.codes import TechnicalCode
from sird_recognition.contracts.ports import (
    ExecuteProfilePort,
    MaterialReaderPort,
    TextReaderChainPort,
)
from sird_recognition.contracts.stages import (
    ExecutionResult,
    ExecutionSpec,
    PreparedDocument,
    PreparedPage,
    StageContext,
)
from sird_recognition.contracts.text_observation import TextObservation
from sird_recognition.runtime import RecognitionError
from sird_recognition.text_reader_errors import (
    TextReaderExecutionError,
    TextReaderLimitError,
    TextReaderUnavailableError,
)

_CAPABILITY_MISMATCH = TechnicalCode.CAPABILITY_MISMATCH


@dataclass(frozen=True, slots=True)
class _ReaderRun:
    """Validated settings shared by one bounded reader pass."""

    language: str
    cpu_threads: int
    deadline: float


def _create_reader_run(
    specification: ExecutionSpec,
    context: StageContext,
    reader_chain: TextReaderChainPort,
) -> _ReaderRun:
    language = specification.reader_language
    if not language or specification.reader_cpu_threads <= 0:
        raise RecognitionError(TechnicalCode.INVALID_CONFIGURATION)
    timeout_limit = context.limits.get("timeout_seconds")
    if timeout_limit is None or timeout_limit <= 0:
        raise RecognitionError(TechnicalCode.INVALID_CONFIGURATION)
    if (
        not specification.reader_order
        or reader_chain.reader_ids != specification.reader_order
    ):
        raise RecognitionError(TechnicalCode.CAPABILITY_MISMATCH)
    return _ReaderRun(
        language=language,
        cpu_threads=specification.reader_cpu_threads,
        deadline=time.monotonic() + timeout_limit,
    )


def _read_text(
    reader_chain: TextReaderChainPort,
    raster: bytes,
    timeout_seconds: float,
    reader_run: _ReaderRun,
) -> TextObservation:
    try:
        return reader_chain.read(
            raster,
            timeout_seconds=timeout_seconds,
            language=reader_run.language,
            cpu_threads=reader_run.cpu_threads,
        )
    except TextReaderUnavailableError as error:
        raise RecognitionError(TechnicalCode.MODEL_UNAVAILABLE) from error
    except TextReaderLimitError as error:
        raise RecognitionError(
            TechnicalCode.EXECUTION_LIMIT_EXCEEDED
        ) from error
    except TextReaderExecutionError as error:
        raise RecognitionError(
            TechnicalCode.EXECUTION_ERROR,
            retryable=True,
        ) from error


class ReaderAwareExecuteProfile(ExecuteProfilePort):
    """Run the declared reader stage before a profile delegate."""

    def __init__(
        self,
        delegate: ExecuteProfilePort,
        reader_chain: TextReaderChainPort,
        material_reader: MaterialReaderPort,
    ) -> None:
        self._delegate = delegate
        self._reader_chain = reader_chain
        self._material_reader = material_reader

    def execute(
        self,
        document: PreparedDocument,
        specification: ExecutionSpec,
        context: StageContext,
        *,
        observations: tuple[TextObservation, ...] = (),
    ) -> ExecutionResult:
        """Load authorized rasters, read text, then run the delegate."""
        applied_observations = observations
        if "read" in specification.stage_names:
            applied_observations = self._read_observations(
                document, specification, context
            )
        execution_result = self._delegate.execute(
            document,
            specification,
            context,
            observations=applied_observations,
        )
        if not applied_observations:
            return execution_result
        metadata = dict(execution_result.execution_metadata)
        metadata["text_observations"] = tuple(
            _safe_observation_metadata(observation)
            for observation in applied_observations
        )
        return replace(execution_result, execution_metadata=metadata)

    def _read_observations(
        self,
        document: PreparedDocument,
        specification: ExecutionSpec,
        context: StageContext,
    ) -> tuple[TextObservation, ...]:
        reader_run = _create_reader_run(
            specification,
            context,
            self._reader_chain,
        )
        return tuple(
            self._read_page(page, specification, reader_run)
            for page in document.pages
            if page.status == "prepared"
        )

    def _read_page(
        self,
        page: PreparedPage,
        specification: ExecutionSpec,
        reader_run: _ReaderRun,
    ) -> TextObservation:
        if not page.prepared_artifact:
            raise RecognitionError(TechnicalCode.MATERIAL_UNAVAILABLE)
        if reader_run.deadline - time.monotonic() <= 0:
            raise RecognitionError(TechnicalCode.EXECUTION_LIMIT_EXCEEDED)
        raster = self._load_raster(
            page.prepared_artifact,
            page.checksum,
        )
        remaining = reader_run.deadline - time.monotonic()
        if remaining <= 0:
            raise RecognitionError(TechnicalCode.EXECUTION_LIMIT_EXCEEDED)
        observation = _read_text(
            self._reader_chain,
            raster,
            remaining,
            reader_run,
        )
        return _validate_observation(
            observation,
            specification,
            reader_run.language,
        )

    def _load_raster(self, artifact_ref: str, checksum: str) -> bytes:
        try:
            raster = self._material_reader.read(
                artifact_ref,
                expected_checksum=checksum,
            )
        except Exception as error:
            raise RecognitionError(
                TechnicalCode.MATERIAL_UNAVAILABLE
            ) from error
        if not isinstance(raster, bytes) or not raster:
            raise RecognitionError(TechnicalCode.MATERIAL_UNAVAILABLE)
        return raster


def _validate_observation(
    observation: TextObservation,
    specification: ExecutionSpec,
    language: str,
) -> TextObservation:
    descriptor = observation.descriptor
    expected_implementation = specification.implementation_checksums.get(
        observation.adapter_id
    )
    expected_model = specification.reader_model_revisions.get(
        observation.adapter_id
    )
    if observation.language != language or descriptor is None:
        raise RecognitionError(_CAPABILITY_MISMATCH)
    if expected_implementation:
        implementation_matches = (
            descriptor.implementation_checksum == expected_implementation
        )
    else:
        implementation_matches = False
    if implementation_matches is False:
        raise RecognitionError(_CAPABILITY_MISMATCH)
    if descriptor.model_revision != expected_model:
        raise RecognitionError(_CAPABILITY_MISMATCH)
    return observation


def _safe_observation_metadata(
    observation: TextObservation,
) -> dict[str, object]:
    descriptor = observation.descriptor
    model_revision = None if descriptor is None else descriptor.model_revision
    return {
        "adapter_id": observation.adapter_id,
        "adapter_version": observation.adapter_version,
        "language": observation.language,
        "model_revision": model_revision,
        "capabilities": tuple(sorted(observation.capabilities)),
        "skipped_reader_ids": observation.skipped_reader_ids,
    }
