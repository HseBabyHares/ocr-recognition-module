"""Parsing helpers for Tesseract TSV output."""

from __future__ import annotations

from sird_recognition._tesseract_support import decode_output
from sird_recognition._tesseract_tsv_rows import parse_rows, raw_text
from sird_recognition.contracts.text_observation import TextRegion


def parse_tsv(
    output: object,
) -> tuple[
    str,
    tuple[TextRegion, ...],
    tuple[float, ...],
]:
    parsed_rows = tuple(parse_rows(decode_output(output)))
    regions = tuple(region for _, region in parsed_rows)
    scores = tuple(
        region.confidence
        for _, region in parsed_rows
        if region.confidence is not None
    )
    return raw_text(parsed_rows), regions, scores
