from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from sird_recognition.contracts.text_observation import TextObservation
from sird_recognition.tesseract_text_reader import TesseractTextReader
from sird_recognition.text_reader_chain import (
    TextReaderChain,
    create_tesseract_first_chain,
)
from sird_recognition.text_reader_errors import (
    TextReaderExecutionError,
    TextReaderLimitError,
    TextReaderUnavailableError,
)

OCR_TIMEOUT = 10.0
CHAIN_TIMEOUT = 1.0
EXHAUSTED_TIMEOUT = 0
SINGLE_CPU = 1
DUAL_CPU = 2
IMAGE_SIZE = "900x120"
FONT_SIZE = "42"
TESSERACT_ID = "tesseract"
FALLBACK_ID = "fallback"
IMPLEMENTATION_CHECKSUM = "sha256:tesseract-test"
TESSDATA_CHECKSUM = "sha256:rus-eng-test"
ANNOTATION_OFFSET = "+0+0"


TSV_HEADER = (
    b"level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
    b"left\ttop\twidth\theight\tconf\ttext\n"
)
TSV_WORD = b"5\t1\t1\t1\t1\t1\t10\t20\t100\t30\t95.0\tSNILS\n"

DEFAULT_STDOUT = TSV_HEADER + TSV_WORD
IMAGE_BYTES = b"image-bytes"
OCR_LANGUAGE = "rus+eng"
CHAIN_IMAGE = b"image"
UNUSED_TEXT = "unused"


class RecordingRunner:
    def __init__(
        self,
        *,
        return_code: int = 0,
        stdout: bytes = DEFAULT_STDOUT,
        stderr: bytes = b"",
    ) -> None:
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
        self.calls: list[Any] = []

    def __call__(self, command: tuple[str, ...], **runner_options: Any) -> Any:
        self.calls.append((command, runner_options))
        return subprocess.CompletedProcess(
            command,
            self.return_code,
            stdout=self.stdout,
            stderr=self.stderr,
        )


class FakeReader:
    def __init__(
        self,
        reader_id: str,
        observation: TextObservation,
        *,
        unavailable: bool = False,
        execution_error: bool = False,
    ) -> None:
        self.adapter_id = reader_id
        self.observation = observation
        self.unavailable = unavailable
        self.execution_error = execution_error
        self.calls = 0

    def read(
        self,
        image: bytes,
        *,
        timeout_seconds: float,
        language: str,
        cpu_threads: int,
    ) -> TextObservation:
        if self.unavailable:
            raise TextReaderUnavailableError("reader unavailable")
        if self.execution_error:
            raise TextReaderExecutionError("reader failed")
        self.calls += 1
        return self.observation


def make_reader(runner: Any) -> TesseractTextReader:
    return TesseractTextReader(
        implementation_checksum=IMPLEMENTATION_CHECKSUM,
        tessdata_checksum=TESSDATA_CHECKSUM,
        runner=runner,
    )


def timeout_runner(command: tuple[str, ...], **timeout_options: Any) -> Any:
    raise subprocess.TimeoutExpired(command, timeout_options["timeout"])


class TestTesseractReader:
    def test_tesseract_text_observation(self) -> None:
        runner = RecordingRunner()
        reader = make_reader(runner)

        observation = reader.read(
            IMAGE_BYTES,
            timeout_seconds=OCR_TIMEOUT,
            language=OCR_LANGUAGE,
            cpu_threads=DUAL_CPU,
        )

        call_options = runner.calls[0][1]
        assert (
            observation.raw_text,
            observation.adapter_id,
            observation.language,
            observation.descriptor is not None,
            getattr(observation.descriptor, "model_revision", None),
            observation.capabilities,
            observation.regions is not None,
            observation.word_scores,
            call_options["input"],
            call_options["env"]["OMP_THREAD_LIMIT"],
        ) == (
            "SNILS",
            TESSERACT_ID,
            OCR_LANGUAGE,
            True,
            TESSDATA_CHECKSUM,
            frozenset(("text", "text_regions", "word_scores")),
            True,
            (0.95,),
            IMAGE_BYTES,
            "2",
        )

    def test_tsv_preserves_lines_across_paragraphs(self) -> None:
        tsv_output = TSV_HEADER + (
            b"5\t1\t1\t1\t1\t1\t10\t20\t100\t30\t95.0\tFIRST\n"
            b"5\t1\t1\t2\t1\t1\t10\t60\t100\t30\t95.0\tSECOND\n"
        )
        observation = make_reader(RecordingRunner(stdout=tsv_output)).read(
            IMAGE_BYTES,
            timeout_seconds=OCR_TIMEOUT,
            language=OCR_LANGUAGE,
            cpu_threads=SINGLE_CPU,
        )

        assert observation.raw_text == "FIRST\nSECOND"

    def test_missing_language_is_unavailable(self) -> None:
        reader = make_reader(
            RecordingRunner(
                return_code=SINGLE_CPU,
                stderr=(
                    b"Error opening data file "
                    b"/usr/share/tessdata/rus.traineddata"
                ),
            )
        )

        with pytest.raises(TextReaderUnavailableError):
            reader.read(
                IMAGE_BYTES,
                timeout_seconds=OCR_TIMEOUT,
                language="rus",
                cpu_threads=SINGLE_CPU,
            )

    def test_timeout_maps_to_limit_error(self) -> None:
        with pytest.raises(TextReaderLimitError):
            make_reader(timeout_runner).read(
                IMAGE_BYTES,
                timeout_seconds=OCR_TIMEOUT,
                language="rus",
                cpu_threads=SINGLE_CPU,
            )


class TestReaderChain:
    def test_chain_prefers_first_reader(self) -> None:
        tesseract = FakeReader(
            TESSERACT_ID,
            TextObservation("first", TESSERACT_ID, "test-first"),
        )
        fallback = FakeReader(
            FALLBACK_ID,
            TextObservation("second", FALLBACK_ID, "test-second"),
        )
        chain = TextReaderChain((tesseract, fallback))

        observation = chain.read(
            CHAIN_IMAGE,
            timeout_seconds=CHAIN_TIMEOUT,
            language=OCR_LANGUAGE,
            cpu_threads=SINGLE_CPU,
        )

        assert observation.raw_text == "first"
        assert observation.skipped_reader_ids == ()
        assert tesseract.calls == 1
        assert fallback.calls == 0

    def test_chain_rejects_exhausted_deadline(self) -> None:
        reader = FakeReader(
            TESSERACT_ID,
            TextObservation(UNUSED_TEXT, TESSERACT_ID, "test-deadline"),
        )

        with pytest.raises(TextReaderLimitError):
            TextReaderChain((reader,)).read(
                CHAIN_IMAGE,
                timeout_seconds=EXHAUSTED_TIMEOUT,
                language=OCR_LANGUAGE,
                cpu_threads=SINGLE_CPU,
            )

    def test_chain_falls_back_when_unavailable(self) -> None:
        unavailable = FakeReader(
            "unavailable",
            TextObservation(UNUSED_TEXT, "unavailable", "test-unavailable"),
            unavailable=True,
        )
        fallback = FakeReader(
            FALLBACK_ID,
            TextObservation("fallback-text", FALLBACK_ID, "test-fallback"),
        )
        chain = TextReaderChain((unavailable, fallback))

        observation = chain.read(
            CHAIN_IMAGE,
            timeout_seconds=CHAIN_TIMEOUT,
            language=OCR_LANGUAGE,
            cpu_threads=SINGLE_CPU,
        )

        assert observation.raw_text == "fallback-text"
        assert observation.adapter_id == FALLBACK_ID
        assert observation.skipped_reader_ids == ("unavailable",)
        assert fallback.calls == 1

    def test_chain_propagates_execution_failure(self) -> None:
        failed = FakeReader(
            TESSERACT_ID,
            TextObservation(UNUSED_TEXT, TESSERACT_ID, "test-failure"),
            execution_error=True,
        )
        fallback = FakeReader(
            FALLBACK_ID,
            TextObservation(UNUSED_TEXT, FALLBACK_ID, "test-fallback"),
        )

        with pytest.raises(TextReaderExecutionError):
            TextReaderChain((failed, fallback)).read(
                CHAIN_IMAGE,
                timeout_seconds=CHAIN_TIMEOUT,
                language=OCR_LANGUAGE,
                cpu_threads=SINGLE_CPU,
            )
        assert fallback.calls == 0

    def test_factory_order(self) -> None:
        fallback = FakeReader(
            FALLBACK_ID,
            TextObservation("fallback", FALLBACK_ID, "test-factory"),
        )

        chain = create_tesseract_first_chain(
            implementation_checksum=IMPLEMENTATION_CHECKSUM,
            tessdata_checksum=TESSDATA_CHECKSUM,
            fallbacks=(fallback,),
        )

        assert chain.reader_ids == (TESSERACT_ID, FALLBACK_ID)


@pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="tesseract unavailable"
)
def test_live_tesseract_reads_cyrillic_snils() -> None:
    languages = subprocess.run(
        ["tesseract", "--list-langs"],
        check=True,
        capture_output=True,
    ).stdout.decode()
    if "rus" not in languages.split():
        pytest.skip("Tesseract rus language data unavailable")
    if shutil.which("convert") is None:
        pytest.skip("ImageMagick convert unavailable")
    fixture_text = (
        (Path(__file__).parent / "fixtures/ocr/tesseract_output.txt")
        .read_text(encoding="utf-8")
        .strip()
    )
    image = subprocess.run(
        [
            "convert",
            "-size",
            IMAGE_SIZE,
            "xc:white",
            "-font",
            "DejaVu-Sans",
            "-fill",
            "black",
            "-pointsize",
            FONT_SIZE,
            "-gravity",
            "West",
            "-annotate",
            ANNOTATION_OFFSET,
            fixture_text,
            "png:-",
        ],
        check=True,
        capture_output=True,
    ).stdout
    observation = TesseractTextReader(
        implementation_checksum=IMPLEMENTATION_CHECKSUM,
        tessdata_checksum=TESSDATA_CHECKSUM,
    ).read(
        image,
        timeout_seconds=OCR_TIMEOUT,
        language=OCR_LANGUAGE,
        cpu_threads=SINGLE_CPU,
    )

    normalized = observation.raw_text.replace(" ", "").replace("-", "")
    assert "123456789" in normalized
    assert observation.regions
    assert observation.word_scores
