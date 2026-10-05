"""Private predicates for candidate label and region binding."""

from collections.abc import Sequence

from sird_recognition.candidate_contracts import CandidateField, CandidateSpan

BindingContext = tuple[
    list[str],
    list[tuple[int, int]],
    dict[CandidateField, tuple[str, ...]],
]

_RELATED_NAME_DISTANCE = 150


def has_related_name(
    candidate: CandidateSpan,
    candidate_values: tuple[CandidateSpan, ...],
) -> bool:
    """Check whether a nearby full-name span supports this candidate."""
    return any(
        related_candidate.field is CandidateField.FULL_NAME
        and related_candidate is not candidate
        and related_candidate.observation_id == candidate.observation_id
        and abs(related_candidate.start - candidate.start)
        <= _RELATED_NAME_DISTANCE
        for related_candidate in candidate_values
    )


def _line_index(
    candidate: CandidateSpan,
    offsets: list[tuple[int, int]],
) -> int | None:
    for index, (start, end) in enumerate(offsets):
        if candidate.start < end and candidate.end > start:
            return index
    return None


def _context_lines(
    candidate: CandidateSpan,
    lines: list[str],
    line_index: int,
) -> Sequence[str]:
    lookback = 4 if candidate.field is CandidateField.FULL_NAME else 1
    return lines[
        max(0, line_index - lookback) : min(
            len(lines),
            line_index + 2,
        )
    ]


def _line_context(
    candidate: CandidateSpan,
    binding_context: BindingContext,
) -> str | None:
    line_index = _line_index(candidate, binding_context[1])
    if line_index is None:
        return None
    return " ".join(
        _context_lines(candidate, binding_context[0], line_index),
    )


def is_bound(
    candidate: CandidateSpan,
    candidate_values: tuple[CandidateSpan, ...],
    name_run_ids: set[int],
    binding_context: BindingContext,
) -> bool:
    """Determine whether a candidate has an explicit binding."""
    if candidate.region is not None:
        return True
    if id(candidate) in name_run_ids:
        return True
    if candidate.field is CandidateField.FULL_NAME and has_related_name(
        candidate, candidate_values
    ):
        return True
    context = _line_context(candidate, binding_context)
    if context is None:
        return False
    normalized_context = " ".join(context.casefold().split())
    return any(
        label in normalized_context
        for label in binding_context[2].get(candidate.field, ())
    )
