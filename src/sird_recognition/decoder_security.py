"""Fail-closed guards around local document decoder implementations.

This module only enforces a local policy boundary. It does not provide an
operating-system sandbox, workload identity, or decoder implementation.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType


class DecoderSecurityError(ValueError):
    """A decoder request or result violated the local security boundary."""


class DecoderPolicyError(DecoderSecurityError):
    """The decoder policy is invalid or does not allow the requested
    decoder."""


class DecoderInputError(DecoderSecurityError):
    """Decoder input was not bounded bytes."""


class DecoderOutputError(DecoderSecurityError):
    """Decoder output was malformed or exceeded a configured bound."""


@dataclass(frozen=True, slots=True)
class DecoderPolicy:
    """Finite decoder limits and an explicit decoder allow-list.

    The three access flags are deliberately exposed and must remain false.
    A deployment adapter can inspect them without inferring policy from an
    absent field.
    """

    max_compressed_bytes: int
    max_width: int
    max_height: int
    max_pixels: int
    max_pages: int
    max_output_bytes: int
    allowed_decoder_ids: Collection[str]
    allow_network: bool = False
    allow_model_catalog: bool = False
    allow_reference_data: bool = False

    def __post_init__(self) -> None:
        for limit_name in (
            "max_compressed_bytes",
            "max_width",
            "max_height",
            "max_pixels",
            "max_pages",
            "max_output_bytes",
        ):
            self._positive_limit(getattr(self, limit_name), limit_name)
        object.__setattr__(
            self,
            "allowed_decoder_ids",
            self._non_empty_ids(self.allowed_decoder_ids),
        )
        for flag_name in (
            "allow_network",
            "allow_model_catalog",
            "allow_reference_data",
        ):
            flag_value = getattr(self, flag_name)
            if flag_value is not False:
                raise DecoderPolicyError(f"{flag_name} must remain disabled")

    @classmethod
    def _positive_limit(cls, limit_value: object, name: str) -> int:
        if (
            isinstance(limit_value, bool)
            or not isinstance(limit_value, int)
            or limit_value <= 0
        ):
            raise DecoderPolicyError(
                f"{name} must be a finite positive integer"
            )
        return limit_value

    @classmethod
    def _non_empty_ids(
        cls,
        decoder_ids: Collection[str],
    ) -> frozenset[str]:
        if isinstance(decoder_ids, str):
            raise DecoderPolicyError(
                "allowed_decoder_ids must be non-empty strings"
            )
        try:
            normalized_ids = frozenset(decoder_ids)
        except (TypeError, ValueError) as exc:
            raise DecoderPolicyError(
                "allowed_decoder_ids must be non-empty strings"
            ) from exc
        if not normalized_ids or any(
            not isinstance(decoder_id, str) or not decoder_id.strip()
            for decoder_id in normalized_ids
        ):
            raise DecoderPolicyError(
                "allowed_decoder_ids must be non-empty strings"
            )
        return normalized_ids

    @classmethod
    def _bounded_dimension(
        cls,
        dimension_value: object,
        maximum: int,
        error_message: str,
    ) -> int:
        if (
            isinstance(dimension_value, bool)
            or not isinstance(dimension_value, int)
            or dimension_value <= 0
            or dimension_value > maximum
        ):
            raise DecoderOutputError(error_message)
        return dimension_value

    @classmethod
    def _validate_input(
        cls,
        policy: DecoderPolicy,
        decoder_id: str,
        compressed: bytes,
    ) -> None:
        if decoder_id not in policy.allowed_decoder_ids:
            raise DecoderPolicyError("decoder is not allowlisted")
        if not isinstance(compressed, bytes):
            raise DecoderInputError("decoder input must be bytes")
        if len(compressed) > policy.max_compressed_bytes:
            raise DecoderInputError("compressed input exceeds policy limit")


@dataclass(frozen=True, slots=True)
class DecodedRaster:
    """Decoder output metadata and bounded pixel payload.

    ``pixels`` may be a byte payload or an integer pixel count. Integer pixel
    counts are useful for adapters that retain raster data outside this guard
    and must include an explicit ``output_bytes`` value.
    """

    width: int
    height: int
    pixels: bytes | int
    pages: int = 1
    output_bytes: int | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.metadata, Mapping):
            object.__setattr__(
                self, "metadata", MappingProxyType(dict(self.metadata))
            )

    @property
    def pixel_count(self) -> int:
        """Return the pixel count represented by this result."""
        if isinstance(self.pixels, bytes):
            return len(self.pixels)
        return self.pixels

    @classmethod
    def _bounded_output_size(
        cls,
        output_size: object,
        maximum: int,
    ) -> int:
        if (
            isinstance(output_size, bool)
            or not isinstance(output_size, int)
            or output_size <= 0
            or output_size > maximum
        ):
            raise DecoderOutputError("decoded output exceeds byte limit")
        return output_size

    @classmethod
    def _payload_output_size(
        cls,
        pixels: bytes,
        output_size: int | None,
        maximum: int,
    ) -> int:
        payload_size = len(pixels)
        if output_size is not None and output_size != payload_size:
            raise DecoderOutputError(
                "decoded output byte metadata does not match payload"
            )
        return cls._bounded_output_size(payload_size, maximum)

    @classmethod
    def _declared_output_size(
        cls,
        output_size: int | None,
        maximum: int,
    ) -> int:
        if output_size is None:
            raise DecoderOutputError("decoded output byte count is missing")
        return cls._bounded_output_size(output_size, maximum)


DecoderCallable = Callable[[bytes], DecodedRaster]


class DecoderSandbox:
    """Inject one decoder behind pre- and post-invocation policy guards."""

    __slots__ = ("_policy", "_decoder_id", "_decoder")

    def __init__(
        self,
        policy: DecoderPolicy,
        decoder_id: str,
        decoder: DecoderCallable,
    ) -> None:
        if not isinstance(policy, DecoderPolicy):
            raise TypeError("policy must be a DecoderPolicy")
        if not isinstance(decoder_id, str) or not decoder_id.strip():
            raise DecoderPolicyError("decoder_id must be a non-empty string")
        if not callable(decoder):
            raise TypeError("decoder must be callable")
        self._policy = policy
        self._decoder_id = decoder_id
        self._decoder = decoder

    @property
    def policy(self) -> DecoderPolicy:
        return self._policy

    @property
    def decoder_id(self) -> str:
        return self._decoder_id

    def decode(self, compressed: bytes) -> DecodedRaster:
        """Decode bounded bytes and return bounded raster metadata."""
        DecoderPolicy._validate_input(
            self._policy,
            self._decoder_id,
            compressed,
        )
        failure = object()
        try:
            decoded_output: object = self._decoder(compressed)
        except Exception:
            decoded_output = failure
        if decoded_output is failure:
            raise DecoderSecurityError("decoder invocation failed")
        return self._validate_output(decoded_output)

    def _validate_dimensions(self, raster: DecodedRaster) -> None:
        width = DecoderPolicy._bounded_dimension(
            raster.width,
            self._policy.max_width,
            "decoded width exceeds policy",
        )
        height = DecoderPolicy._bounded_dimension(
            raster.height,
            self._policy.max_height,
            "decoded height exceeds policy",
        )
        pages = DecoderPolicy._bounded_dimension(
            raster.pages,
            self._policy.max_pages,
            "decoded pages exceed policy",
        )
        DecoderPolicy._bounded_dimension(
            raster.pixel_count,
            self._policy.max_pixels,
            "decoded pixels exceed policy",
        )
        if width * height * pages > self._policy.max_pixels:
            raise DecoderOutputError("decoded dimensions exceed pixel limit")

    def _output_size(self, raster: DecodedRaster) -> int:
        maximum = self._policy.max_output_bytes
        if isinstance(raster.pixels, bytes):
            return DecodedRaster._payload_output_size(
                raster.pixels,
                raster.output_bytes,
                maximum,
            )
        return DecodedRaster._declared_output_size(
            raster.output_bytes,
            maximum,
        )

    def _validate_output(self, decoded_output: object) -> DecodedRaster:
        if not isinstance(decoded_output, DecodedRaster):
            raise DecoderOutputError("decoder output has an invalid type")
        self._validate_dimensions(decoded_output)
        output_size = self._output_size(decoded_output)
        return replace(decoded_output, output_bytes=output_size)
