"""Rule/model reconciliation for full-name evidence."""

from __future__ import annotations

from sird_recognition._snils_field_candidates import candidate_values
from sird_recognition._snils_labels import _Patterns
from sird_recognition._snils_name_rules import name_candidates
from sird_recognition._snils_name_values import (
    candidate_name_values,
    strict_name_subset,
)
from sird_recognition.candidate_extraction import CandidateField, CandidateSpan


def _name_tokens(name_candidate: str) -> tuple[str, ...]:
    return tuple(_Patterns.word.findall(name_candidate.casefold()))


def supported_name_candidates(
    rule_candidates: set[str],
    model_tokens: set[str],
    texts: tuple[str, ...],
) -> set[str]:
    """Keep rule names supported by model tokens and observations."""
    supported = {
        name_candidate
        for name_candidate in rule_candidates
        if model_tokens
        and model_tokens.issubset(set(_name_tokens(name_candidate)))
    }
    if not supported:
        return set()
    support = {
        name_candidate: sum(
            name_candidate in name_candidates((text,)) for text in texts
        )
        for name_candidate in supported
    }
    best = max(support.values())
    return {
        name_candidate
        for name_candidate, count in support.items()
        if count == best
    }


def combined_name_candidates(
    texts: tuple[str, ...],
    bound_candidates: tuple[CandidateSpan, ...],
) -> set[str]:
    """Build maximal contiguous model name candidates per observation."""
    observation_ids = tuple(
        f"observation-{index}" for index in range(len(texts))
    )
    raw_candidates = candidate_name_values(
        bound_candidates, texts, observation_ids
    )
    return {
        name_candidate
        for name_candidate in raw_candidates
        if not any(
            strict_name_subset(name_candidate, other)
            for other in raw_candidates
            if other != name_candidate
        )
    }


def choose_name_candidates(
    rule_candidates: set[str],
    model_candidates: set[str],
    combined_candidates: set[str],
    texts: tuple[str, ...],
) -> set[str]:
    """Reconcile model and rule candidates without repairing OCR text."""
    model_tokens = {
        token
        for name_candidate in model_candidates | combined_candidates
        for token in _Patterns.word.findall(name_candidate.casefold())
    }
    supported = supported_name_candidates(rule_candidates, model_tokens, texts)
    if supported:
        return supported
    if len(model_candidates) == 1:
        return set(model_candidates)
    if not combined_candidates:
        return rule_candidates | model_candidates
    filtered = {
        name_candidate
        for name_candidate in model_candidates
        if not any(
            strict_name_subset(name_candidate, combined)
            for combined in combined_candidates
        )
    }
    filtered.update(combined_candidates)
    return filtered if len(filtered) == 1 else rule_candidates | filtered


def resolve_name(
    texts: tuple[str, ...],
    bound_candidates: tuple[CandidateSpan, ...],
) -> tuple[str | None, set[str]]:
    """Resolve a unique full name and retain ambiguity evidence."""
    rule_candidates = name_candidates(texts)
    model_candidates = candidate_values(
        bound_candidates, CandidateField.FULL_NAME
    )
    combined_candidates = combined_name_candidates(texts, bound_candidates)
    candidates = choose_name_candidates(
        rule_candidates, model_candidates, combined_candidates, texts
    )
    name = next(iter(candidates)) if len(candidates) == 1 else None
    return name, candidates
