"""Low-level contiguous span operations for SNILS name candidates."""

from __future__ import annotations

import re

from sird_recognition._snils_labels import _Patterns
from sird_recognition.candidate_extraction import CandidateSpan


def valid_span(candidate: CandidateSpan, text: str) -> bool:
    """Return whether a candidate exactly covers its source text."""
    return (
        candidate.start >= 0
        and candidate.start < candidate.end
        and candidate.end <= len(text)
        and text[candidate.start : candidate.end] == candidate.raw_text
    )


def joined_end(
    text: str, previous: CandidateSpan, current: CandidateSpan
) -> int | None:
    """Return the end of adjacent spans when their gap is punctuation only."""
    gap = text[previous.end : current.start]
    if re.search(r"[^\W\s.,;:()\-'\"»«]+", gap):
        return None
    return current.end


def combined_tokens(
    text: str, first_span: CandidateSpan, combined_end: int
) -> list[str]:
    """Extract normalized word tokens from a combined candidate span."""
    return _Patterns.word.findall(text[first_span.start : combined_end])


def value_for_span(
    text: str,
    spans: list[CandidateSpan],
    first_index: int,
    offset: int,
    current_span: CandidateSpan,
) -> tuple[str | None, bool]:
    """Build one candidate value and indicate when expansion should stop."""
    combined_end = current_span.end
    if offset:
        combined_end = joined_end(
            text, spans[first_index + offset - 1], current_span
        )
        if combined_end is None:
            return None, True
    tokens = combined_tokens(text, spans[first_index], combined_end)
    within_bounds = (
        _Patterns.combined_token_min
        <= len(tokens)
        <= _Patterns.combined_token_max
    )
    span_value = " ".join(tokens) if within_bounds else None
    return span_value, len(tokens) >= _Patterns.combined_token_max


def values_from_start(
    text: str, spans: list[CandidateSpan], first_index: int
) -> set[str]:
    """Build all bounded values beginning at one matching span."""
    name_values: set[str] = set()
    for offset, current_span in enumerate(spans[first_index:]):
        span_value, stop_after_span = value_for_span(
            text,
            spans,
            first_index,
            offset,
            current_span,
        )
        if span_value is not None:
            name_values.add(span_value)
        if stop_after_span:
            break
    return name_values
