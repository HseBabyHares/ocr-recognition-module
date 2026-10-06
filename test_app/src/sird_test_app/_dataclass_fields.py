"""Private support for hidden dataclass field specifications."""

from __future__ import annotations

from collections.abc import Iterator, Mapping


class _DataclassFieldSpec:
    def __init__(
        self,
        public_name: str,
        annotation: object,
        default: object,
        insert_after: str | None = None,
    ) -> None:
        self.public_name = public_name
        self.annotation = annotation
        self.default = default
        self.insert_after = insert_after


class _DataclassFieldDescriptor:
    def __init__(self, public_name: str, default: object) -> None:
        self._storage_name = f"_{public_name}"
        self._default = default

    def __get__(
        self,
        instance: object | None,
        owner: type[object] | None = None,
    ) -> object:
        if instance is None:
            return self._default
        try:
            return object.__getattribute__(instance, self._storage_name)
        except AttributeError:
            return self._default

    def __set__(self, instance: object, field_content: object) -> None:
        object.__setattr__(instance, self._storage_name, field_content)


def _iter_annotations(
    namespace: Mapping[str, object],
    annotations: Mapping[str, object],
) -> Iterator[tuple[str, object]]:
    field_specs = tuple(
        member
        for member in namespace.values()
        if isinstance(member, _DataclassFieldSpec)
    )
    for field_spec in field_specs:
        if field_spec.insert_after is None:
            yield field_spec.public_name, field_spec.annotation
    for member_name, annotation in annotations.items():
        yield member_name, annotation
        for field_spec in field_specs:
            if field_spec.insert_after == member_name:
                yield field_spec.public_name, field_spec.annotation


def _inject_dataclass_fields[RecordT](
    record_class: type[RecordT],
) -> type[RecordT]:
    namespace = record_class.__dict__
    annotations = namespace.get("__annotations__", {})
    record_class.__annotations__ = dict(
        _iter_annotations(namespace, annotations),
    )
    field_specs = tuple(
        member
        for member in namespace.values()
        if isinstance(member, _DataclassFieldSpec)
    )
    for field_spec in field_specs:
        setattr(
            record_class,
            field_spec.public_name,
            _DataclassFieldDescriptor(
                field_spec.public_name,
                field_spec.default,
            ),
        )
    return record_class
