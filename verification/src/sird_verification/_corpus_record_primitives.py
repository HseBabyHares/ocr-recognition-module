"""Primitive provenance records used by corpus manifests."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from sird_verification._corpus_enums import (
    FieldPresence,
    FieldReadability,
    presence,
    readability,
)
from sird_verification._corpus_serialization import (
    digest,
    freeze,
    jsonable,
    non_empty,
)

_GENERATOR_KEY = "generator"
_TEMPLATE_KEY = "template"
_PARAMETERS_KEY = "parameters"
_SEED_KEY = "seed"


@dataclass(frozen=True, slots=True)
class PageProvenance:
    """Identity and visible metadata for one rasterized page."""

    page_id: str
    source_id: str
    page_index: int = 0
    raster_id: str = ""
    rasterization_version: str = ""
    decoder_version: str = ""
    checksum: str = ""
    visible_geometry: Mapping[str, Any] = MappingProxyType({})
    observed_checksum: str | None = None

    def __post_init__(self) -> None:
        non_empty(self.page_id, "page_id")
        non_empty(self.source_id, "source_id")
        if self.page_index < 0:
            raise ValueError("page_index must be non-negative")
        if (
            self.checksum
            and self.observed_checksum
            and self.checksum != self.observed_checksum
        ):
            raise ValueError("page checksum does not match observed checksum")
        object.__setattr__(
            self,
            "visible_geometry",
            freeze(self.visible_geometry),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return manifest-safe page metadata."""
        return {
            "page_id": self.page_id,
            "source_id": self.source_id,
            "page_index": self.page_index,
            "raster_id": self.raster_id,
            "rasterization_version": self.rasterization_version,
            "decoder_version": self.decoder_version,
            "checksum": self.checksum,
            "visible_geometry": jsonable(self.visible_geometry),
        }


@dataclass(frozen=True, slots=True)
class FieldLabel:
    """Observed field metadata; protected labels are not stored here."""

    name: str
    present: FieldPresence | bool | str = FieldPresence.UNKNOWN
    readability: FieldReadability | str = FieldReadability.DISPUTED
    observed_text: str | None = None
    normalized_value: str | None = None

    def __post_init__(self) -> None:
        non_empty(self.name, "field name")
        object.__setattr__(self, "present", presence(self.present))
        object.__setattr__(
            self,
            "readability",
            readability(self.readability),
        )

    def as_dict(self, *, include_observation: bool = True) -> dict[str, Any]:
        """Return field metadata without protected reference labels."""
        field_metadata: dict[str, Any] = {
            "name": self.name,
            "present": self.present.value,
            "readability": self.readability.value,
        }
        if include_observation:
            field_metadata["observed_text"] = self.observed_text
            field_metadata["normalized_value"] = self.normalized_value
        return field_metadata


def _has_duplicate_transform_arguments(
    positional: tuple[Any, ...],
    named_arguments: Mapping[str, Any],
) -> bool:
    has_excess_positional = len(positional) > 2
    has_duplicate_parameters = positional and _PARAMETERS_KEY in named_arguments
    has_duplicate_seed = len(positional) > 1 and _SEED_KEY in named_arguments
    return (
        has_excess_positional
        or has_duplicate_parameters
        or has_duplicate_seed
    )


def _transform_argument_values(
    positional: tuple[Any, ...],
    named_arguments: dict[str, Any],
) -> tuple[Any, Any]:
    if _has_duplicate_transform_arguments(positional, named_arguments):
        raise TypeError("duplicate or excessive transform arguments")
    parameter_values = (
        positional[0]
        if positional
        else named_arguments.pop(_PARAMETERS_KEY, MappingProxyType({}))
    )
    seed_value = (
        positional[1]
        if len(positional) > 1
        else named_arguments.pop(_SEED_KEY, 0)
    )
    if named_arguments:
        raise TypeError("unexpected transform arguments")
    return parameter_values, seed_value


@dataclass(frozen=True, slots=True, init=False)
class SyntheticTransform:
    """Reproducible synthetic transformation provenance."""

    generator: str
    template: str
    _parameter_values: Mapping[str, Any] = field(
        default=MappingProxyType({}),
        repr=False,
    )
    seed: int = 0

    def __init__(
        self,
        generator: str,
        template: str,
        *positional: Any,
        **named_arguments: Any,
    ) -> None:
        parameter_value, seed_value = _transform_argument_values(
            positional,
            named_arguments,
        )
        object.__setattr__(self, "generator", generator)
        object.__setattr__(self, "template", template)
        object.__setattr__(self, "_parameter_values", parameter_value)
        object.__setattr__(self, "seed", seed_value)
        self.__post_init__()

    def __post_init__(self) -> None:
        non_empty(self.generator, _GENERATOR_KEY)
        non_empty(self.template, _TEMPLATE_KEY)
        object.__setattr__(
            self,
            "_parameter_values",
            freeze(self._parameter_values),
        )

    @property
    def fingerprint(self) -> str:
        """Stable identity for the generator, parameters, and seed."""
        return digest(
            {
                _GENERATOR_KEY: self.generator,
                _TEMPLATE_KEY: self.template,
                _PARAMETERS_KEY: self.parameters,
                _SEED_KEY: self.seed,
            },
        )

    def as_dict(self) -> dict[str, Any]:
        """Return transform provenance as manifest-safe data."""
        return {
            _GENERATOR_KEY: self.generator,
            _TEMPLATE_KEY: self.template,
            _PARAMETERS_KEY: jsonable(self.parameters),
            _SEED_KEY: self.seed,
            "fingerprint": self.fingerprint,
        }

    @property
    def _transform_parameters(self) -> Mapping[str, Any]:
        """Return immutable transform parameters."""
        return self._parameter_values


setattr(
    SyntheticTransform,
    "parameters",
    property(SyntheticTransform._transform_parameters.fget),
)
