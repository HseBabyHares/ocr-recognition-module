"""Optional GLiNER-backed candidate extractor implementation."""

import importlib
import time
from collections.abc import Mapping
from contextlib import suppress
from typing import TypedDict, Unpack, cast

from sird_recognition import candidate_contracts
from sird_recognition._candidate_inference import (
    InferenceContext,
    run_inference,
)
from sird_recognition._candidate_model import (
    labels,
    predict_capabilities,
    prediction_kwargs,
)
from sird_recognition._candidate_resources import ResourceContext
from sird_recognition._candidate_translation import TranslationSource
from sird_recognition.candidate_config import validate_settings
from sird_recognition.contracts.text_observation import TextObservation

CandidateStageLimitError = candidate_contracts.CandidateStageLimitError
CandidateStageTelemetry = candidate_contracts.CandidateStageTelemetry
CandidateStageUnavailableError = (
    candidate_contracts.CandidateStageUnavailableError
)
CandidateTelemetrySink = candidate_contracts.CandidateTelemetrySink
CandidateSpan = candidate_contracts.CandidateSpan

_INJECTED_SOURCE = "injected"
_ZERO_SECONDS = float(0)

DEFAULT_MODEL_ID = "urchade/gliner_multi-v2.1"
DEFAULT_MODEL_REVISION = "443d26d654e0324125a96bebd8e796c14ff2efe6"
DEFAULT_SCORE_SCALE = "model_raw"
DEFAULT_MAX_TEXT_LENGTH = 32_000
DEFAULT_MAX_CANDIDATES = 64
DEFAULT_MAX_MODEL_CALLS = 1
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MEMORY_LIMIT_BYTES = 4 * 1024 * 1024 * 1024
DEFAULT_CPU_THREADS = 1
DEFAULT_RESOURCE_REVISION = "unknown"


class _ExtractorSettings(TypedDict, total=False):
    model_id: str | None
    model_revision: str | None
    local_files_only: bool
    fail_closed: bool
    max_text_length: int
    max_candidates: int
    max_model_calls: int
    timeout_seconds: float
    memory_limit_bytes: int
    cpu_threads: int
    threshold: float
    score_scale: str
    resource_revision: str
    request_id: str
    attempt_id: str
    stage_id: str
    telemetry: CandidateTelemetrySink | None


def _configured_identifier(
    configured: str | None,
    model: object | None,
) -> str | None:
    if configured:
        return configured
    if model is not None:
        return _INJECTED_SOURCE
    return None


def _load_model(
    model_id: str,
    revision: str,
    local_files_only: bool,
) -> object:
    try:
        return importlib.import_module("gliner").GLiNER.from_pretrained(
            model_id,
            revision=revision,
            local_files_only=local_files_only,
        )
    except Exception as error:
        raise CandidateStageUnavailableError(
            "candidate model or tokenizer is unavailable",
        ) from error


class GLiNERCandidateExtractor:
    """Lazily invoke an optional GLiNER model over bounded OCR text."""

    def __init__(
        self,
        model: object | None = None,
        **settings: Unpack[_ExtractorSettings],
    ) -> None:
        options = _extract_settings(settings)
        validate_settings(options)
        self._model = model
        self._model_id = _configured_identifier(options["model_id"], model)
        self._model_revision = _configured_identifier(
            options["model_revision"], model
        )
        self._local_files_only = options["local_files_only"]
        self._fail_closed = options["fail_closed"]
        self._max_text_length = options["max_text_length"]
        self._max_candidates = options["max_candidates"]
        self._max_model_calls = options["max_model_calls"]
        self._timeout_seconds = float(options["timeout_seconds"])
        self._memory_limit_bytes = options["memory_limit_bytes"]
        self._cpu_threads = options["cpu_threads"]
        self._resource_revision = options["resource_revision"]
        self._request_id = options["request_id"]
        self._attempt_id = options["attempt_id"]
        self._stage_id = options["stage_id"]
        self._telemetry = options["telemetry"]
        self._threshold = options["threshold"]
        self._score_scale = options["score_scale"]
        self._loaded = model is not None
        self._model_calls = 0
        self._resources = ResourceContext(
            self._timeout_seconds,
            self._memory_limit_bytes,
            self._max_candidates,
            self._emit,
            TranslationSource(
                self._score_scale,
                self._model_id or _INJECTED_SOURCE,
                self._model_revision or _INJECTED_SOURCE,
            ),
        )

    def extract(
        self, observation: TextObservation
    ) -> tuple[CandidateSpan, ...]:
        if not isinstance(observation, TextObservation):
            raise TypeError("observation must be a TextObservation")
        if self._model_calls >= self._max_model_calls:
            self._emit(
                "limited",
                _ZERO_SECONDS,
                0,
                "model_call_limit",
                "limited",
            )
            raise CandidateStageLimitError(
                "candidate model-call limit exceeded"
            )
        try:
            model = self._get_model()
        except CandidateStageUnavailableError:
            self._emit(
                "failed",
                _ZERO_SECONDS,
                0,
                "model_unavailable",
                "unavailable",
            )
            raise
        text = observation.raw_text[: self._max_text_length]
        return self._run_inference(model, text, observation)

    def _run_inference(
        self,
        model: object,
        text: str,
        observation: TextObservation,
    ) -> tuple[CandidateSpan, ...]:
        started = time.monotonic()
        self._model_calls += 1
        self._emit(
            "started",
            _ZERO_SECONDS,
            0,
            "inference_started",
            "within_limit",
        )
        return run_inference(
            InferenceContext(
                self._resources,
                self._emit,
                self._predict,
                started,
            ),
            model,
            text,
            observation,
        )

    def _emit(
        self,
        event: str,
        elapsed_seconds: float,
        candidate_count: int,
        reason_code: str,
        limit_state: str,
    ) -> None:
        if self._telemetry is None:
            return
        record = CandidateStageTelemetry(
            self._request_id,
            self._attempt_id,
            self._stage_id,
            event,
            self._model_id,
            self._model_revision,
            self._resource_revision,
            elapsed_seconds,
            candidate_count,
            limit_state,
            reason_code,
        )
        with suppress(Exception):
            self._telemetry(record)

    def _get_model(self) -> object:
        if self._model is not None:
            return self._model
        if self._loaded:
            raise CandidateStageUnavailableError(
                "candidate model is unavailable"
            )
        self._loaded = True
        if not self._model_id:
            raise CandidateStageUnavailableError(
                "candidate model was not explicitly configured"
            )
        revision = self._model_revision or DEFAULT_MODEL_REVISION
        self._model = _load_model(
            self._model_id,
            revision,
            self._local_files_only,
        )
        self._model_revision = revision
        self._resources.source = TranslationSource(
            self._score_scale,
            self._model_id or _INJECTED_SOURCE,
            self._model_revision or _INJECTED_SOURCE,
        )
        return self._model

    def _predict(self, model: object, text: str) -> object:
        predict = getattr(model, "predict_entities", None)
        if not callable(predict):
            raise CandidateStageUnavailableError(
                "candidate model does not provide predict_entities"
            )
        capabilities = predict_capabilities(predict)
        kwargs = prediction_kwargs(
            capabilities,
            self._threshold,
            self._cpu_threads,
        )
        labels_for_model = list(labels())
        return (
            predict(text, labels_for_model, **kwargs)
            if kwargs
            else predict(text, labels_for_model)
        )


def _extract_settings(
    settings: Mapping[str, object],
) -> _ExtractorSettings:
    defaults = {
        "model_id": None,
        "model_revision": None,
        "local_files_only": True,
        "fail_closed": True,
        "max_text_length": DEFAULT_MAX_TEXT_LENGTH,
        "max_candidates": DEFAULT_MAX_CANDIDATES,
        "max_model_calls": DEFAULT_MAX_MODEL_CALLS,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "memory_limit_bytes": DEFAULT_MEMORY_LIMIT_BYTES,
        "cpu_threads": DEFAULT_CPU_THREADS,
        "threshold": _ZERO_SECONDS,
        "score_scale": DEFAULT_SCORE_SCALE,
        "resource_revision": DEFAULT_RESOURCE_REVISION,
        "request_id": "unknown",
        "attempt_id": "unknown",
        "stage_id": "candidate-extraction",
        "telemetry": None,
    }
    unexpected = set(settings).difference(defaults)
    if unexpected:
        name = next(iter(unexpected))
        raise TypeError(f"unexpected keyword argument: {name}")
    defaults.update(settings)
    return cast(_ExtractorSettings, defaults)
