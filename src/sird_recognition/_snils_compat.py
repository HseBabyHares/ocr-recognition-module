"""Compatibility routing for historical private service helpers."""

from __future__ import annotations

from collections.abc import Callable

from sird_recognition._snils_checks import snils_candidates
from sird_recognition._snils_dates import date_values
from sird_recognition._snils_decode import (
    decode_image,
    perspective_image,
    validate_input,
)
from sird_recognition._snils_field_candidates import (
    birth_date_candidates,
    candidate_birth_dates,
    candidate_labels,
    candidate_values,
    canonical_place,
    optional_unique_birth_place,
)
from sird_recognition._snils_geometry import (
    document_quad,
    green_document_quad,
    luminance_quad,
    order_points,
    warp,
    warp_has_content,
)
from sird_recognition._snils_images import encode_image, repair_glare_image
from sird_recognition._snils_name_rules import name_candidates
from sird_recognition._snils_name_values import (
    candidate_name_values,
    strict_name_subset,
)
from sird_recognition._snils_types import (
    ImageLimits,
    SnilsRecognitionResult,
    SnilsRecognitionStatus,
)


def refused_result(
    diagnostics: tuple[str, ...], variants: int, observations: int
) -> SnilsRecognitionResult:
    """Construct a refusal with stable field defaults."""
    return SnilsRecognitionResult(
        SnilsRecognitionStatus.REFUSED,
        None,
        None,
        None,
        diagnostics,
        variants,
        observations,
    )


def _decode_helpers(limits: ImageLimits) -> dict[str, Callable[..., object]]:
    return {
        "_validate_input": lambda image_bytes: validate_input(
            image_bytes, limits
        ),
        "_decode": lambda image_bytes: decode_image(image_bytes, limits),
        "_perspective": lambda frame: perspective_image(frame, limits),
        "_warp": lambda frame, points: warp(frame, points, limits),
    }


def _geometry_helpers() -> dict[str, Callable[..., object]]:
    return {
        "_warp_has_content": warp_has_content,
        "_green_document_quad": green_document_quad,
        "_document_quad": document_quad,
        "_luminance_quad": luminance_quad,
        "_order_points": order_points,
        "_repair_glare": repair_glare_image,
        "_encode": encode_image,
    }


def _field_helpers() -> dict[str, Callable[..., object]]:
    return {
        "_name_candidates": name_candidates,
        "_birth_date_candidates": birth_date_candidates,
        "_candidate_labels": candidate_labels,
        "_canonical_place": canonical_place,
        "_candidate_values": candidate_values,
        "_candidate_birth_dates": candidate_birth_dates,
        "_optional_unique_birth_place": optional_unique_birth_place,
    }


def _name_helpers() -> dict[str, Callable[..., object]]:
    return {
        "_snils_candidates": snils_candidates,
        "_strict_name_subset": strict_name_subset,
        "_candidate_name_values": candidate_name_values,
        "_optional_unique_name": lambda candidate_texts: _unique(
            name_candidates(candidate_texts)
        ),
        "_optional_unique_birth_date": lambda candidate_texts: _unique(
            birth_date_candidates(candidate_texts)
        ),
        "_refused": refused_result,
        "_date_values": date_values,
    }


def private_helper(name: str, limits: ImageLimits) -> Callable[..., object]:
    """Return the historical helper callable selected by name."""
    handlers = {
        **_decode_helpers(limits),
        **_geometry_helpers(),
        **_field_helpers(),
        **_name_helpers(),
    }
    try:
        return handlers[name]
    except KeyError as error:
        raise AttributeError(name) from error


def _unique(candidates: set[str]) -> str | None:
    return next(iter(candidates)) if len(candidates) == 1 else None
