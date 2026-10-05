"""Row-level parsing helpers for Tesseract TSV output."""

from sird_recognition.contracts.text_observation import TextRegion
from sird_recognition.text_reader_errors import TextReaderExecutionError

_ParsedLineKey = tuple[int, int, int]
_ParsedRows = tuple[tuple[_ParsedLineKey, TextRegion], ...]

_TSV_MIN_COLUMNS = 12
_TSV_TEXT_INDEX = 11
_TSV_BOUNDS_START = 6
_TSV_BOUNDS_END = 10
_TSV_CONFIDENCE_INDEX = 10
_TSV_BLOCK_INDEX = 2
_TSV_PARAGRAPH_INDEX = 3
_TSV_LINE_INDEX = 4


def parse_rows(text: str):
    for row in text.splitlines()[1:]:
        parsed = parse_row(row)
        if parsed is not None:
            yield parsed


def parse_row(
    row: str,
) -> tuple[tuple[int, int, int], TextRegion] | None:
    columns = row.split("\t")
    if len(columns) < _TSV_MIN_COLUMNS:
        return None
    text = columns[_TSV_TEXT_INDEX].strip()
    if not text:
        return None
    line_key = parse_line_key(columns)
    bounds = parse_bounds(columns[_TSV_BOUNDS_START:_TSV_BOUNDS_END])
    confidence = parse_confidence(columns[_TSV_CONFIDENCE_INDEX])
    return line_key, TextRegion(
        left=bounds[0],
        top=bounds[1],
        width=bounds[2],
        height=bounds[3],
        line_number=line_key[-1],
        text=text,
        confidence=confidence,
    )


def parse_line_key(columns: list[str]) -> tuple[int, int, int]:
    try:
        return (
            int(columns[_TSV_BLOCK_INDEX]),
            int(columns[_TSV_PARAGRAPH_INDEX]),
            int(columns[_TSV_LINE_INDEX]),
        )
    except ValueError as error:
        raise TextReaderExecutionError(
            "tesseract returned malformed TSV line number"
        ) from error


def parse_bounds(columns: list[str]) -> tuple[int, int, int, int]:
    try:
        parsed_bounds = tuple(int(coordinate) for coordinate in columns)
    except ValueError as error:
        raise TextReaderExecutionError(
            "tesseract returned malformed TSV geometry"
        ) from error
    if len(parsed_bounds) != 4:
        raise TextReaderExecutionError(
            "tesseract returned malformed TSV geometry"
        )
    return (
        parsed_bounds[0],
        parsed_bounds[1],
        parsed_bounds[2],
        parsed_bounds[3],
    )


def parse_confidence(text: str) -> float | None:
    try:
        confidence = float(text)
    except ValueError as error:
        raise TextReaderExecutionError(
            "tesseract returned malformed TSV confidence"
        ) from error
    return None if confidence < 0 else confidence / 100.0


def raw_text(parsed_rows: _ParsedRows) -> str:
    raw_lines = group_words(parsed_rows)
    return "\n".join(" ".join(words) for words in raw_lines.values())


def group_words(
    parsed_rows: _ParsedRows,
) -> dict[tuple[int, int, int], list[str]]:
    raw_lines: dict[tuple[int, int, int], list[str]] = {}
    for line_key, region in parsed_rows:
        raw_lines.setdefault(line_key, []).append(region.text)
    return raw_lines
