"""Private helpers for multi-line name candidate binding."""

import re

from sird_recognition.candidate_contracts import CandidateField, CandidateSpan
from sird_recognition.contracts.text_observation import TextObservation

_MAX_NAME_RUN = 3
_NAME_WORD_PATTERN = re.compile(r"[^\W\d_]+", re.UNICODE)
_GAP_WORD_PATTERN = re.compile(r"[^\W\s.,;:()'\"»«-]+", re.UNICODE)


def _is_single_word(candidate: CandidateSpan) -> bool:
    return len(_NAME_WORD_PATTERN.findall(candidate.raw_text)) == 1


def _extend_name_run(
    observation: TextObservation,
    run: list[CandidateSpan],
    candidate: CandidateSpan,
) -> bool:
    previous = run[-1]
    if candidate.observation_id != previous.observation_id:
        return False
    gap = observation.raw_text[previous.end : candidate.start]
    if _GAP_WORD_PATTERN.search(gap):
        return False
    run.append(candidate)
    return True


def _qualifying_name_ids(run: list[CandidateSpan]) -> set[int]:
    if len(run) < 2 or not all(
        _is_single_word(name_span) for name_span in run
    ):
        return set()
    return {id(name_span) for name_span in run}


def name_run(
    observation: TextObservation,
    full_name_candidates: list[CandidateSpan],
    first_index: int,
) -> set[int]:
    """Find contiguous candidate spans that form a full name."""
    run = [full_name_candidates[first_index]]
    qualifying_ids: set[int] = set()
    for name_candidate in full_name_candidates[first_index + 1 :]:
        if not _extend_name_run(observation, run, name_candidate):
            break
        qualifying_ids.update(_qualifying_name_ids(run))
        if len(run) == _MAX_NAME_RUN:
            break
    return qualifying_ids


def name_run_ids(
    observation: TextObservation,
    candidate_values: tuple[CandidateSpan, ...],
) -> set[int]:
    """Return candidate identities participating in a name run."""
    full_name_candidates = sorted(
        (
            candidate
            for candidate in candidate_values
            if candidate.field is CandidateField.FULL_NAME
        ),
        key=lambda candidate: (candidate.start, candidate.end),
    )
    name_run_ids: set[int] = set()
    for first_index, _ in enumerate(full_name_candidates):
        name_run_ids.update(
            name_run(observation, full_name_candidates, first_index),
        )
    return name_run_ids
