from __future__ import annotations

from pathlib import Path
from typing import cast

import cv2
import numpy as np

from sird_recognition.candidate_extraction import (
    CandidateField,
    CandidateSpan,
)
from sird_recognition.contracts.text_observation import (
    TextObservation,
    TextRegion,
)
from sird_recognition.snils_recognition import (
    SnilsRecognitionResult,
    SnilsRecognitionService,
    SnilsRecognitionStatus,
)

_FORMATTED_SNILS = "112-233-445 95"
_VALID_SNILS = "11223344595"
_VALID_BIRTH_DATE = "1980-04-03"
_TIMEOUT_SECONDS = 2.0
_MAX_INPUT_BYTES = 4
_MODEL_RAW = "model_raw"
_FAKE_ADAPTER = "fake"
_TEST_SOURCE = "test"
_REVISION = "revision"
_TEXT_ENCODING = "utf-8"
_IMAGE_CHANNELS = 3
_IMAGE_WIDTH = 420
_IMAGE_HEIGHT = 240
_IMAGE_BACKGROUND = 235
_LARGE_IMAGE_WIDTH = 600
_LARGE_IMAGE_HEIGHT = 400
_LARGE_IMAGE_BACKGROUND = 35
_GREEN_IMAGE_BACKGROUND = 25
_TEXT_SCORE = 0.8
_REGION_SCORE = 0.9
_DEFAULT_VARIANTS = 4
_EMPTY_VARIANTS = 0
_IMAGE_POINTS = (
    (35, 30),
    (385, 15),
    (400, 215),
    (20, 225),
)
_IMAGE_POLY_COLOR = (255, 255, 255)
_TEXT_ORIGIN = (70, 125)
_TEXT_SCALE = 1
_TEXT_COLOR = (0, 0, 0)
_TEXT_THICKNESS = 2
_LARGE_POINTS = (
    (85, 55),
    (520, 30),
    (565, 340),
    (45, 370),
)
_GREEN_POINTS = (
    (85, 55),
    (520, 45),
    (555, 345),
    (50, 370),
)
_LARGE_POLY_COLOR = (235, 235, 235)
_LARGE_BORDER_COLOR = (0, 0, 0)
_LARGE_BORDER_THICKNESS = 8
_GREEN_POLY_COLOR = (120, 190, 175)
_GREEN_BORDER_COLOR = (35, 70, 65)
_GREEN_BORDER_THICKNESS = 6
_REGION_SIZE = 10


class FakeReader:
    def __init__(self, text: str) -> None:
        self.text = text
        self.images: list[bytes] = []

    def read(
        self,
        image: bytes,
        *,
        timeout_seconds: float,
        language: str,
        cpu_threads: int,
    ) -> TextObservation:
        self.images.append(image)
        return TextObservation(self.text, _FAKE_ADAPTER, _TEST_SOURCE)

    @classmethod
    def candidate_text(cls) -> str:
        return (
            Path(__file__).parent / "fixtures/ocr/candidate_fields.txt"
        ).read_text(encoding=_TEXT_ENCODING)

    @classmethod
    def candidate_name_place(cls, text: str) -> tuple[str, str]:
        lines = text.splitlines()
        return (
            lines[0].split(": ", 1)[1],
            lines[3].split(", ", 1)[1],
        )

    @classmethod
    def candidate_dates(cls, text: str) -> tuple[str, str]:
        lines = text.splitlines()
        registration_line = lines[2].split(": ", 1)[1]
        birth_line = lines[3].split(": ", 1)[1]
        birth_date = birth_line.split(",", 1)[0]
        return registration_line, birth_date

    @classmethod
    def snils_fixture_lines(cls) -> list[str]:
        fixture = (
            Path(__file__).parent / "fixtures/ocr/snils_fields.txt"
        ).read_text(encoding=_TEXT_ENCODING)
        return fixture.splitlines()

    @classmethod
    def snils_name_place(cls) -> tuple[str, str]:
        lines = cls.snils_fixture_lines()
        return (
            lines[0],
            lines[3].split(", ", 1)[1],
        )


class CandidateFake:
    def __init__(
        self,
        spans: tuple[CandidateSpan, ...] | None = None,
        error: bool = False,
    ) -> None:
        self.spans = spans or ()
        self.error = error

    def extract(
        self, observation: TextObservation
    ) -> tuple[CandidateSpan, ...]:
        if self.error:
            raise RuntimeError("model unavailable")
        return tuple(
            CandidateSpan(
                candidate.field,
                candidate.raw_text,
                candidate.start,
                candidate.end,
                candidate.score,
                candidate.score_scale,
                observation.adapter_id,
                candidate.model_id,
                candidate.model_revision,
                candidate.region,
            )
            for candidate in self.spans
        )

    @classmethod
    def fragmented_extractor(cls, text: str) -> CandidateFake:
        return cls(
            tuple(
                _TestHelpers.span(text, CandidateField.FULL_NAME, fragment)
                for fragment in ("СИДОРОВ", "ПЕТР", "ПЕТРОВИЧ")
            )
        )

    @classmethod
    def candidate_extractor(
        cls,
        text: str,
        first_field: CandidateField,
        first_text: str,
        second_field: CandidateField,
        second_text: str,
    ) -> CandidateFake:
        return cls(
            (
                _TestHelpers.span(text, first_field, first_text),
                _TestHelpers.span(text, second_field, second_text),
            )
        )


class _TestHelpers:
    @classmethod
    def fixture_text(cls) -> str:
        return (
            Path(__file__).parent / "fixtures/ocr/snils_fields.txt"
        ).read_text(encoding=_TEXT_ENCODING)

    @classmethod
    def image_bytes(cls) -> bytes:
        image = np.full(
            (_IMAGE_HEIGHT, _IMAGE_WIDTH, _IMAGE_CHANNELS),
            _IMAGE_BACKGROUND,
            dtype=np.uint8,
        )
        points = np.array(_IMAGE_POINTS, dtype=np.int32)
        cv2.fillPoly(image, [points], _IMAGE_POLY_COLOR)
        cv2.putText(
            image,
            "SNILS",
            _TEXT_ORIGIN,
            cv2.FONT_HERSHEY_SIMPLEX,
            _TEXT_SCALE,
            _TEXT_COLOR,
            _TEXT_THICKNESS,
        )
        return cv2.imencode(".jpg", image)[1].tobytes()

    @classmethod
    def span(
        cls,
        text: str,
        field: CandidateField,
        field_text: str,
    ) -> CandidateSpan:
        start = text.index(field_text)
        return CandidateSpan(
            field,
            field_text,
            start,
            start + len(field_text),
            _TEXT_SCORE,
            _MODEL_RAW,
            _FAKE_ADAPTER,
            _TEST_SOURCE,
            _REVISION,
        )

    @classmethod
    def large_document_bytes(cls) -> bytes:
        image = np.full(
            (_LARGE_IMAGE_HEIGHT, _LARGE_IMAGE_WIDTH, _IMAGE_CHANNELS),
            _LARGE_IMAGE_BACKGROUND,
            dtype=np.uint8,
        )
        points = np.array(_LARGE_POINTS, dtype=np.int32)
        cv2.fillPoly(image, [points], _LARGE_POLY_COLOR)
        cv2.polylines(
            image, [points], True, _LARGE_BORDER_COLOR, _LARGE_BORDER_THICKNESS
        )
        return cv2.imencode(".jpg", image)[1].tobytes()

    @classmethod
    def green_document_bytes(cls) -> bytes:
        image = np.full(
            (_LARGE_IMAGE_HEIGHT, _LARGE_IMAGE_WIDTH, _IMAGE_CHANNELS),
            _GREEN_IMAGE_BACKGROUND,
            dtype=np.uint8,
        )
        points = np.array(_GREEN_POINTS, dtype=np.int32)
        cv2.fillPoly(image, [points], _GREEN_POLY_COLOR)
        cv2.polylines(
            image, [points], True, _GREEN_BORDER_COLOR, _GREEN_BORDER_THICKNESS
        )
        return cv2.imencode(".jpg", image)[1].tobytes()

    @classmethod
    def recognize(
        cls,
        text: str,
        candidate_extractor: CandidateFake | None = None,
    ):
        service = SnilsRecognitionService(
            FakeReader(text), candidate_extractor=candidate_extractor
        )
        return service.recognize_image(
            cls.image_bytes(), timeout_seconds=_TIMEOUT_SECONDS
        )

    @classmethod
    def recognize_variants(
        cls,
        text: str,
    ) -> tuple[FakeReader, SnilsRecognitionResult]:
        reader = FakeReader(text)
        service = SnilsRecognitionService(
            reader, max_variants=_DEFAULT_VARIANTS
        )
        recognition = service.recognize_image(
            cls.image_bytes(), timeout_seconds=_TIMEOUT_SECONDS
        )
        return reader, recognition


class TestSnilsBasics(_TestHelpers):
    def test_snils_normalization_and_checksum(self) -> None:
        assert (
            SnilsRecognitionService.normalize_snils(_FORMATTED_SNILS)
            == _VALID_SNILS
        )
        assert SnilsRecognitionService.is_valid_snils(_VALID_SNILS)
        assert not SnilsRecognitionService.is_valid_snils("00000000000")
        assert not SnilsRecognitionService.is_valid_snils("11223344596")

    def test_formatted_snils_extracts_variants(self) -> None:
        reader, recognition = self.recognize_variants(self.fixture_text())
        fixture_name, fixture_place = FakeReader.snils_name_place()

        assert (
            recognition.status is SnilsRecognitionStatus.VERIFIED,
            recognition.snils_number,
            recognition.full_name,
            recognition.birth_place,
            recognition.variant_count,
            len(reader.images),
            all(reader.images),
        ) == (
            True,
            _VALID_SNILS,
            fixture_name,
            fixture_place,
            _DEFAULT_VARIANTS,
            _DEFAULT_VARIANTS,
            True,
        )

    def test_invalid_checksum_refused(self) -> None:
        recognition = self.recognize("112-233-445 96")

        assert (
            recognition.status is SnilsRecognitionStatus.REFUSED,
            recognition.snils_number,
            "snils_missing_or_invalid" in recognition.diagnostics,
        ) == (True, None, True)

    def test_unreadable_image_refused(self) -> None:
        recognition = self.recognize("")

        assert (
            recognition.refused,
            recognition.snils_number,
        ) == (True, None)

    def test_oversized_input_refused_before_reader(self) -> None:
        reader = FakeReader(_FORMATTED_SNILS)
        service = SnilsRecognitionService(
            reader, max_input_bytes=_MAX_INPUT_BYTES
        )

        recognition = service.recognize_image(
            b"too large", timeout_seconds=_TIMEOUT_SECONDS
        )

        assert recognition.refused
        assert recognition.variant_count == _EMPTY_VARIANTS
        assert reader.images == []

    def test_registration_date_not_birth_date(self) -> None:
        text = f"Повреждено\n{_FORMATTED_SNILS}\nДата регистрации: 15.06.2020"
        recognition = self.recognize(text)
        assert (
            recognition.status is SnilsRecognitionStatus.VERIFIED,
            recognition.snils_number,
            recognition.birth_date,
        ) == (True, _VALID_SNILS, None)

    def test_valid_snils_with_unreadable_fields(self) -> None:
        fixture_path = (
            Path(__file__).parent
            / "fixtures/ocr/valid_snils_optional_fields_unreadable.txt"
        )
        fixture_text = fixture_path.read_text(encoding=_TEXT_ENCODING)
        recognition = self.recognize(fixture_text)
        assert (
            recognition.status is SnilsRecognitionStatus.VERIFIED,
            recognition.snils_number,
            recognition.full_name,
            recognition.birth_place,
            recognition.birth_date,
        ) == (True, _VALID_SNILS, None, None, None)


class TestCandidateBindings(_TestHelpers):
    def test_candidate_unique_name_and_place(self) -> None:
        text = FakeReader.candidate_text()
        name, place = FakeReader.candidate_name_place(text)
        extractor = CandidateFake.candidate_extractor(
            text,
            CandidateField.FULL_NAME,
            name,
            CandidateField.BIRTH_PLACE,
            place,
        )
        recognition = self.recognize(text, extractor)
        assert (
            recognition.status is SnilsRecognitionStatus.VERIFIED,
            recognition.full_name,
            recognition.birth_place,
        ) == (True, name, place)

    def test_candidate_birth_ignores_registration(self) -> None:
        text = FakeReader.candidate_text()
        registration_date, birth_date = FakeReader.candidate_dates(text)
        extractor = CandidateFake.candidate_extractor(
            text,
            CandidateField.REGISTRATION_DATE,
            registration_date,
            CandidateField.BIRTH_DATE,
            birth_date,
        )
        recognition = self.recognize(text, extractor)
        assert recognition.birth_date == _VALID_BIRTH_DATE

    def test_candidate_failure_preserves_snils(self) -> None:
        recognition = self.recognize(
            _FORMATTED_SNILS,
            CandidateFake(error=True),
        )
        assert recognition.snils_number == _VALID_SNILS
        assert recognition.diagnostics == (
            "candidate_extractor_unavailable",
            "snils_checksum_valid",
        )

    def test_conflicting_names_refused(self) -> None:
        text = f"ФИО: ИВАНОВ ИВАН\nФИО: ПЕТРОВ ПЁТР\n{_FORMATTED_SNILS}"
        extractor = CandidateFake.candidate_extractor(
            text,
            CandidateField.FULL_NAME,
            "ИВАНОВ ИВАН",
            CandidateField.FULL_NAME,
            "ПЕТРОВ ПЁТР",
        )
        recognition = self.recognize(text, extractor)
        assert (
            recognition.snils_number,
            recognition.full_name,
            "name_ambiguous" in recognition.diagnostics,
        ) == (_VALID_SNILS, None, True)

    def test_multiline_name_resolved(self) -> None:
        text = (
            "Российская Федерация\n"
            "СТРАХОВОЕ СВИДЕТЕЛЬСТВО\n"
            f"{_FORMATTED_SNILS}\n"
            "ФИО. СИДОРОВ\n"
            "ПЕТР\n"
            "ПЕТРОВИЧ\n"
            "Дата и место рождения 23 января 2004\n"
            "г. Москва\n"
            "Дата регистрации 20.08.2012"
        )
        recognition = self.recognize(text)

        assert recognition.full_name == "СИДОРОВ ПЕТР ПЕТРОВИЧ"

    def test_fragmented_name_not_ambiguous(self) -> None:
        text = (
            f"{_FORMATTED_SNILS}\n"
            "ФИО. СИДОРОВ\n"
            "ПЕТР\n"
            "ПЕТРОВИЧ\n"
            "Дата и место рождения 3 апреля 1980"
        )
        extractor = CandidateFake.fragmented_extractor(text)
        recognition = self.recognize(text, extractor)

        assert (
            recognition.full_name,
            "name_ambiguous" not in recognition.diagnostics,
        ) == ("СИДОРОВ ПЕТР ПЕТРОВИЧ", True)

    def test_region_bound_name_retained(self) -> None:
        text = _FORMATTED_SNILS
        candidate = CandidateSpan(
            CandidateField.FULL_NAME,
            "СИДОРОВ ПЕТР",
            0,
            1,
            _REGION_SCORE,
            _MODEL_RAW,
            "synthetic",
            "model",
            _REVISION,
            TextRegion(
                0,
                0,
                _REGION_SIZE,
                _REGION_SIZE,
                1,
                "name",
                _REGION_SCORE,
            ),
        )
        recognition = self.recognize(text, CandidateFake((candidate,)))

        assert recognition.full_name == "СИДОРОВ ПЕТР"


class TestImageCrops(_TestHelpers):
    def test_large_quad_warp(self) -> None:
        service = SnilsRecognitionService(FakeReader(""))
        decoded = cast(
            np.ndarray, service._decode(self.large_document_bytes())
        )
        quad = service._document_quad(decoded)
        warped = cast(np.ndarray, service._perspective(decoded))

        assert quad is not None
        assert warped.shape[1] > warped.shape[0]
        assert (
            warped.shape[1] != decoded.shape[1]
            or warped.shape[0] != decoded.shape[0]
        )

    def test_green_crop_precedes_warp(self) -> None:
        service = SnilsRecognitionService(FakeReader(""))
        decoded = cast(
            np.ndarray, service._decode(self.green_document_bytes())
        )
        green_quad = service._green_document_quad(decoded)
        warped = cast(np.ndarray, service._perspective(decoded))

        assert green_quad is not None
        assert warped.shape[1] != decoded.shape[1]


class TestDateExtraction(_TestHelpers):
    def test_numeric_dates(self) -> None:
        service = SnilsRecognitionService(FakeReader(""))
        assert service._birth_date_candidates(
            ("Дата рождения: 03/04/1980, 04-05-1981, 31.02.1982",)
        ) == {"1980-04-03", "1981-05-04"}

    def test_russian_genitive_months(self) -> None:
        service = SnilsRecognitionService(FakeReader(""))
        months = {
            "января": "01",
            "февраля": "02",
            "марта": "03",
            "апреля": "04",
            "мая": "05",
            "июня": "06",
            "июля": "07",
            "августа": "08",
            "сентября": "09",
            "октября": "10",
            "ноября": "11",
            "декабря": "12",
        }
        text = "\n".join(f"Дата рождения: 1 {month} 1980" for month in months)
        assert service._birth_date_candidates((text,)) == {
            f"1980-{number}-01" for number in months.values()
        }

    def test_birth_label_binds_next_line(self) -> None:
        service = SnilsRecognitionService(FakeReader(""))
        assert service._birth_date_candidates(
            ("Дата рождения:\n3 апреля 1980",)
        ) == {"1980-04-03"}
