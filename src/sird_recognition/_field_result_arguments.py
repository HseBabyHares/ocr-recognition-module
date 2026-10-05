"""Compatibility argument parsing for field outcome records."""

from collections.abc import Mapping
from typing import TypedDict

_VALUE_KEY = "value"
_FieldResultKeywords = TypedDict(
    "_FieldResultKeywords",
    {
        "validations": tuple[object, ...],
        "evidence_refs": tuple[str, ...],
        "diagnostics": tuple[str, ...],
        "required": bool,
        _VALUE_KEY: object | None,
        "field_value": object | None,
    },
    total=False,
)

_METADATA_NAMES = ("validations", "evidence_refs", "diagnostics", "required")
_DEFAULT_METADATA: tuple[object, ...] = ((), (), (), True)


def field_result_arguments(
    positional: tuple[object, ...],
    legacy_kwargs: Mapping[str, object],
) -> tuple[object | None, tuple[object, ...]]:
    """Return the field value and metadata from legacy call forms."""
    if len(positional) > len(_METADATA_NAMES) + 1:
        raise TypeError("too many positional arguments")
    field_value, metadata_positional = _split_field_value(positional)
    keyword_values = dict(legacy_kwargs)
    field_value = _keyword_field_value(field_value, keyword_values)
    metadata = _metadata_values(metadata_positional, keyword_values)
    if keyword_values:
        unexpected = next(iter(keyword_values))
        raise TypeError(f"unexpected keyword argument: {unexpected}")
    return field_value, metadata


def _split_field_value(
    positional: tuple[object, ...],
) -> tuple[object | None, tuple[object, ...]]:
    if not positional:
        return None, ()
    return positional[0], positional[1:]


def _keyword_field_value(
    field_value: object | None,
    keyword_values: dict[str, object],
) -> object | None:
    if "field_value" in keyword_values:
        if field_value is not None:
            raise TypeError("field_value specified more than once")
        field_value = keyword_values.pop("field_value")
    if "value" in keyword_values:
        if field_value is not None:
            raise TypeError("value specified more than once")
        field_value = keyword_values.pop("value")
    return field_value


def _metadata_values(
    positional: tuple[object, ...],
    keyword_values: dict[str, object],
) -> tuple[object, ...]:
    if len(positional) > len(_METADATA_NAMES):
        raise TypeError("too many positional arguments")
    metadata = list(_DEFAULT_METADATA)
    for index, name in enumerate(_METADATA_NAMES):
        if name in keyword_values:
            if index < len(positional):
                raise TypeError(f"{name} specified more than once")
            metadata[index] = keyword_values.pop(name)
    for index, positional_value in enumerate(positional):
        metadata[index] = positional_value
    return tuple(metadata)
