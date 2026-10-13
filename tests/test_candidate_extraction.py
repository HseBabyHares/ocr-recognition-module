from __future__ import annotations

import hashlib
import json
import tracemalloc
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock

import pytest

from sird_recognition.candidate_extraction import (
    CandidateField,
    CandidateSpan,
    CandidateStageLimitError,
    CandidateStageTelemetry,
    CandidateStageUnavailableError,
    GLiNERCandidateExtractor,
    bind_candidates,
)
from sird_recognition.contracts.text_observation import TextObservation

Record = dict[str, object]
ModelCall = tuple[str, list[str], float]
EXPECTED_RAW_SCORE = 0.91
NAME_SCORE = 0.9
BIRTH_DATE_SCORE = 0.8
BIRTH_PLACE_SCORE = 0.4
HIGH_SCORE = 0.99
DUPLICATE_SCORE = 0.7
UNSUPPORTED_SCORE = 99
CHECKSUM_LENGTH = 64
FIXTURE_SOURCE = "fixture"
TEST_ID = "test"
REVISION = "revision"
FIXTURE_RAW_SCALE = "fixture_raw"
MODEL_RAW_SCALE = "model_raw"
LABEL_KEY = "label"
TEXT_KEY = "text"
START_KEY = "start"
END_KEY = "end"
SCORE_KEY = "score"
FULL_NAME_LABEL = "full_name"
BIRTH_DATE_LABEL = "birth_date"
BIRTH_PLACE_LABEL = "birth_place"
SURNAME = "СИДОРОВ"
BIRTH_PLACE = "г. Казань"
UTF8 = "utf-8"


class FakeModel:
    def __init__(
        self,
        records: list[Record] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.records = [] if records is None else records
        self.error = error
        self.calls: list[ModelCall] = []
        self.kwargs: dict[str, object] = {}

    def predict_entities(
        self,
        text: str,
        labels: list[str],
        *,
        threshold: float,
        **kwargs: object,
    ) -> list[Record]:
        if self.error is not None:
            raise self.error
        self.calls.append((text, labels, threshold))
        self.kwargs = kwargs
        return self.records


def _fixture_text() -> str:
    return (Path(__file__).parent / "fixtures/ocr/snils_fields.txt").read_text(
        encoding=UTF8
    )


def _observation(text: str | None = None) -> TextObservation:
    return TextObservation(text or _fixture_text(), FIXTURE_SOURCE, TEST_ID)


def _first_line_candidates() -> tuple[str, int, tuple[CandidateSpan, ...]]:
    text = _fixture_text()
    first_line = text.splitlines()[0]
    start = text.index(first_line)
    model = FakeModel(
        [
            {
                LABEL_KEY: FULL_NAME_LABEL,
                TEXT_KEY: first_line,
                START_KEY: start,
                END_KEY: start + len(first_line),
            }
        ]
    )
    candidates = GLiNERCandidateExtractor(
        model=model,
        model_id="test-model",
        model_revision="test-revision",
    ).extract(_observation(text))
    return text, start, candidates


class TestCandidateExtractionBasics:
    def test_maps_labels_and_offsets(self) -> None:
        text, start, candidates = _first_line_candidates()
        candidate = candidates[0]

        assert (
            len(candidates),
            candidate.field,
            candidate.raw_text,
            (candidate.start, candidate.end),
            candidate.observation_id,
            candidate.model_id,
            candidate.model_revision,
        ) == (
            1,
            CandidateField.FULL_NAME,
            text.splitlines()[0],
            (start, start + len(text.splitlines()[0])),
            FIXTURE_SOURCE,
            "test-model",
            "test-revision",
        )

    def test_model_gets_field_prompts(self) -> None:
        model = FakeModel([])

        GLiNERCandidateExtractor(model=model).extract(
            _observation(_fixture_text())
        )

        assert model.calls[0][1] == [
            "person",
            "date of birth",
            "place of birth",
            "registration date",
        ]

    def test_bounds_model_text_and_candidate_count(self) -> None:
        model = FakeModel(
            [
                {
                    LABEL_KEY: FULL_NAME_LABEL,
                    START_KEY: 0,
                    END_KEY: 1,
                    SCORE_KEY: 1.0,
                },
                {
                    LABEL_KEY: BIRTH_PLACE_LABEL,
                    START_KEY: 1,
                    END_KEY: 2,
                    SCORE_KEY: 2.0,
                },
                {
                    LABEL_KEY: BIRTH_DATE_LABEL,
                    START_KEY: 2,
                    END_KEY: 3,
                    SCORE_KEY: 3.0,
                },
            ]
        )

        extractor = GLiNERCandidateExtractor(
            model=model,
            max_text_length=4,
            max_candidates=2,
        )

        with pytest.raises(CandidateStageLimitError, match="candidate count"):
            extractor.extract(_observation("abcd" * 10))

        assert len(model.calls[0][0]) == 4

    def test_telemetry_cpu_bound(self) -> None:
        model = FakeModel(
            [
                {
                    LABEL_KEY: FULL_NAME_LABEL,
                    START_KEY: 0,
                    END_KEY: 4,
                    SCORE_KEY: BIRTH_DATE_SCORE,
                }
            ]
        )

        events: list[CandidateStageTelemetry] = []
        candidates = GLiNERCandidateExtractor(
            model=model,
            cpu_threads=3,
            request_id="request-1",
            attempt_id="attempt-1",
            stage_id="candidate-stage",
            resource_revision="resource-1",
            telemetry=events.append,
        ).extract(_observation("Иван"))

        event = events[-1]
        assert (
            len(candidates),
            model.kwargs,
            event.event,
            event.request_id,
            event.attempt_id,
            event.stage_id,
            event.resource_revision,
            event.candidate_count,
            hasattr(event, "raw_text"),
            hasattr(event, "image"),
        ) == (
            1,
            {"cpu_threads": 3},
            "completed",
            "request-1",
            "attempt-1",
            "candidate-stage",
            "resource-1",
            1,
            False,
            False,
        )

    def test_call_limit_telemetry(self) -> None:
        events: list[CandidateStageTelemetry] = []
        extractor = GLiNERCandidateExtractor(
            model=FakeModel([]),
            max_model_calls=1,
            telemetry=events.append,
        )

        extractor.extract(_observation(_fixture_text()))
        with pytest.raises(CandidateStageLimitError, match="model-call"):
            extractor.extract(_observation(_fixture_text()))

        event = events[-1]
        assert event.event == "limited"
        assert event.reason_code == "model_call_limit"
        assert not hasattr(event, "raw_text")

    def test_unavailable_model_error(self) -> None:
        with pytest.raises(CandidateStageUnavailableError):
            GLiNERCandidateExtractor().extract(_observation(_fixture_text()))

        with pytest.raises(CandidateStageUnavailableError):
            GLiNERCandidateExtractor(
                model=FakeModel(error=RuntimeError("model is not ready"))
            ).extract(_observation(_fixture_text()))

    def test_score_preserves_raw_scale(self) -> None:
        model = FakeModel(
            [
                {
                    LABEL_KEY: BIRTH_DATE_LABEL,
                    START_KEY: 0,
                    END_KEY: 4,
                    SCORE_KEY: EXPECTED_RAW_SCORE,
                    "score_scale": FIXTURE_RAW_SCALE,
                }
            ]
        )

        candidate = GLiNERCandidateExtractor(model=model).extract(
            _observation("2000")
        )[0]

        assert candidate.score == EXPECTED_RAW_SCORE
        assert candidate.raw_score == EXPECTED_RAW_SCORE
        assert candidate.score_scale == FIXTURE_RAW_SCALE


class TestCandidateExtractionBinding:
    def test_binding_keeps_context(self) -> None:
        text = _fixture_text()
        name = text.splitlines()[0]
        birth_date_line = text.splitlines()[3]
        birth_date_text = birth_date_line.partition(": ")[2].partition(",")[0]
        labels: dict[str, list[str]] = json.loads(
            (
                Path(__file__).parents[1]
                / "src"
                / "sird_recognition"
                / "resources"
                / "ocr_labels.json"
            ).read_text(encoding=UTF8)
        )

        assert [
            candidate.field
            for candidate in bind_candidates(
                _observation(text),
                (
                    CandidateSpan(
                        CandidateField.FULL_NAME,
                        name,
                        text.index(name),
                        text.index(name) + len(name),
                        NAME_SCORE,
                        FIXTURE_RAW_SCALE,
                        FIXTURE_SOURCE,
                        TEST_ID,
                        REVISION,
                    ),
                    CandidateSpan(
                        CandidateField.BIRTH_DATE,
                        birth_date_text,
                        text.index(birth_date_text),
                        text.index(birth_date_text) + len(birth_date_text),
                        BIRTH_DATE_SCORE,
                        FIXTURE_RAW_SCALE,
                        FIXTURE_SOURCE,
                        TEST_ID,
                        REVISION,
                    ),
                ),
                {
                    CandidateField.FULL_NAME: labels["name_label_tokens"],
                    CandidateField.BIRTH_DATE: labels["birth_labels"],
                },
            )
        ] == [CandidateField.BIRTH_DATE]

    def test_name_binds_four_lines_away(self) -> None:
        text = "ФИО\nстрока\nстрока\nСИДОРОВ"
        start = text.index(SURNAME)
        candidate = CandidateSpan(
            CandidateField.FULL_NAME,
            SURNAME,
            start,
            start + len(SURNAME),
            BIRTH_DATE_SCORE,
            MODEL_RAW_SCALE,
            FIXTURE_SOURCE,
            TEST_ID,
            REVISION,
        )

        bound = bind_candidates(
            _observation(text),
            (candidate,),
            {CandidateField.FULL_NAME: ("фио",)},
        )

        assert bound == (candidate,)

    def test_birth_place_binds_label(self) -> None:
        text = "Место рождения: г. Казань\nСвободный текст"
        start = text.index(BIRTH_PLACE)
        candidate = CandidateSpan(
            CandidateField.BIRTH_PLACE,
            BIRTH_PLACE,
            start,
            start + len(BIRTH_PLACE),
            BIRTH_PLACE_SCORE,
            MODEL_RAW_SCALE,
            FIXTURE_SOURCE,
            TEST_ID,
            REVISION,
        )
        assert bind_candidates(
            _observation(text),
            (candidate,),
            {CandidateField.BIRTH_PLACE: ("место рождения",)},
        ) == (candidate,)

    def test_mismatch_drops_candidate(self) -> None:
        text = "Дата регистрации: 15.06.2020"
        start = text.index("15.06.2020")
        candidate = CandidateSpan(
            CandidateField.BIRTH_DATE,
            "15.06.2020",
            start,
            start + len("15.06.2020"),
            HIGH_SCORE,
            MODEL_RAW_SCALE,
            FIXTURE_SOURCE,
            TEST_ID,
            REVISION,
        )
        assert (
            bind_candidates(
                _observation(text),
                (candidate,),
                {CandidateField.BIRTH_DATE: ("дата рождения",)},
            )
            == ()
        )

    def test_duplicate_candidates_are_retained(self) -> None:
        text = "Место рождения: г. Казань"
        start = text.index(BIRTH_PLACE)
        candidate = CandidateSpan(
            CandidateField.BIRTH_PLACE,
            BIRTH_PLACE,
            start,
            start + len(BIRTH_PLACE),
            DUPLICATE_SCORE,
            MODEL_RAW_SCALE,
            FIXTURE_SOURCE,
            TEST_ID,
            REVISION,
        )
        assert (
            len(
                bind_candidates(
                    _observation(text),
                    (candidate, candidate),
                    {CandidateField.BIRTH_PLACE: ("место рождения",)},
                )
            )
            == 2
        )

    def test_unsupported_score_stays_raw(self) -> None:
        model = FakeModel(
            [
                {
                    LABEL_KEY: FULL_NAME_LABEL,
                    START_KEY: 0,
                    END_KEY: 6,
                    SCORE_KEY: UNSUPPORTED_SCORE,
                    "score_scale": "uncalibrated_fixture_units",
                }
            ]
        )
        candidate = GLiNERCandidateExtractor(model=model).extract(
            _observation(SURNAME)
        )[0]
        assert candidate.score == UNSUPPORTED_SCORE
        assert candidate.score_scale == "uncalibrated_fixture_units"


class TestCandidateExtractionProfiles:
    def test_profile_label_checksum(self) -> None:
        labels_path = (
            Path(__file__).parents[1]
            / "src/sird_recognition/resources/ocr_labels.json"
        )
        profile_path = (
            Path(__file__).parents[1]
            / "src/sird_recognition/resources/gliner_profile.json"
        )
        profile = json.loads(profile_path.read_text(encoding=UTF8))
        observed = hashlib.sha256(labels_path.read_bytes()).hexdigest()
        assert observed == profile["ocr_labels_sha256"]

    def test_unavailable_telemetry(self) -> None:
        events: list[CandidateStageTelemetry] = []
        extractor = GLiNERCandidateExtractor(
            model=FakeModel(error=RuntimeError("model is not ready")),
            request_id="req-safe",
            attempt_id="attempt-safe",
            stage_id="gliner",
            model_revision="fixture-revision",
            resource_revision="fixture-resource",
            telemetry=events.append,
        )

        with pytest.raises(CandidateStageUnavailableError):
            extractor.extract(_observation("ИВАНОВ ИВАН"))

        event = events[-1]
        serialized = repr(event)
        assert (
            event.event,
            event.reason_code,
            event.limit_state,
            event.request_id,
            event.attempt_id,
            event.stage_id,
            event.model_revision,
            event.resource_revision,
            "ИВАНОВ" in serialized,
            "raw_text" in serialized,
            "image" in serialized,
        ) == (
            "failed",
            "inference_unavailable",
            "unavailable",
            "req-safe",
            "attempt-safe",
            "gliner",
            "fixture-revision",
            "fixture-resource",
            False,
            False,
            False,
        )

    def test_temporaries_released(self) -> None:
        model = FakeModel(
            [
                {
                    LABEL_KEY: FULL_NAME_LABEL,
                    START_KEY: 0,
                    END_KEY: 6,
                    SCORE_KEY: BIRTH_DATE_SCORE,
                }
            ]
        )
        was_tracing = tracemalloc.is_tracing()
        with ExitStack() as stack:
            if not was_tracing:
                tracemalloc.start()
                stack.callback(tracemalloc.stop)
            GLiNERCandidateExtractor(model=model).extract(
                _observation(SURNAME)
            )
            assert tracemalloc.is_tracing()

    def test_profile_checksums(self) -> None:
        profile_path = (
            Path(__file__).parents[1]
            / "src/sird_recognition/resources/gliner_profile.json"
        )
        profile = json.loads(profile_path.read_text(encoding=UTF8))
        for key in (
            "ocr_labels_sha256",
            "model_safetensors_sha256",
            "tokenizer_config_sha256",
            "backbone_config_sha256",
            "tokenizer_spm_sha256",
        ):
            checksum = profile[key]
            assert (
                isinstance(checksum, str),
                len(checksum),
                all(character in "0123456789abcdef" for character in checksum),
            ) == (True, CHECKSUM_LENGTH, True)

    def test_request_view_resets_call_budget(self) -> None:
        events: list[CandidateStageTelemetry] = []
        shared = GLiNERCandidateExtractor(
            model=FakeModel([]), telemetry=events.append
        )
        shared.extract(_observation())
        first = shared.for_request(request_id="view-1")
        first.extract(_observation())
        second = shared.for_request(request_id="view-2")
        with pytest.raises(CandidateStageLimitError, match="model-call"):
            first.extract(_observation())
        second.extract(_observation())

        request_ids = dict.fromkeys(event.request_id for event in events)
        assert list(request_ids) == ["unknown", "view-1", "view-2"]

    def test_request_views_share_lazy_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        load = Mock(return_value=FakeModel([]))
        monkeypatch.setattr(
            "sird_recognition._candidate_extractor._load_model", load
        )
        shared = GLiNERCandidateExtractor(model_id="lazy-model")
        for _ in range(2):
            shared.for_request().extract(_observation())

        load.assert_called_once()
