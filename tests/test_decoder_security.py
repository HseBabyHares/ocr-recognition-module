from __future__ import annotations

from collections.abc import Collection
from typing import TypedDict, cast
from unittest.mock import Mock

import pytest

from sird_recognition.decoder_security import (
    DecodedRaster,
    DecoderInputError,
    DecoderOutputError,
    DecoderPolicy,
    DecoderPolicyError,
    DecoderSandbox,
    DecoderSecurityError,
)


class _DecoderPolicyValues(TypedDict):
    max_compressed_bytes: int
    max_width: int
    max_height: int
    max_pixels: int
    max_pages: int
    max_output_bytes: int
    allowed_decoder_ids: Collection[str]
    allow_network: bool
    allow_model_catalog: bool
    allow_reference_data: bool


_DECODER_ID = "local-png"
_COMPRESSED_LIMIT = 8
_DIMENSION_LIMIT = 20
_PIXEL_LIMIT = 400
_PAGE_LIMIT = 2
_OUTPUT_LIMIT = 128


def _policy(**changes: object) -> DecoderPolicy:
    policy_args: _DecoderPolicyValues = {
        "max_compressed_bytes": _COMPRESSED_LIMIT,
        "max_width": _DIMENSION_LIMIT,
        "max_height": _DIMENSION_LIMIT,
        "max_pixels": _PIXEL_LIMIT,
        "max_pages": _PAGE_LIMIT,
        "max_output_bytes": _OUTPUT_LIMIT,
        "allowed_decoder_ids": {_DECODER_ID},
        "allow_network": False,
        "allow_model_catalog": False,
        "allow_reference_data": False,
    }
    policy_args.update(cast(_DecoderPolicyValues, changes))
    return DecoderPolicy(**policy_args)


def _output_decoder(_encoded: bytes) -> DecodedRaster:
    return DecodedRaster(
        width=2,
        height=3,
        pages=1,
        pixels=b"pixels",
        metadata={"mode": "L"},
    )


def _failing_decoder(_encoded_input: bytes) -> DecodedRaster:
    raise RuntimeError("decoder saw secret input")


def _invalid_rasters() -> tuple[DecodedRaster, ...]:
    return (
        DecodedRaster(width=_DIMENSION_LIMIT + 1, height=1, pixels=1),
        DecodedRaster(width=1, height=_DIMENSION_LIMIT + 1, pixels=1),
        DecodedRaster(width=1, height=1, pages=_PAGE_LIMIT + 1, pixels=1),
        DecodedRaster(width=1, height=1, pixels=_PIXEL_LIMIT + 1),
    ) + (
        DecodedRaster(
            width=1,
            height=1,
            pixels=1,
            output_bytes=_OUTPUT_LIMIT + 1,
        ),
        DecodedRaster(
            width=1,
            height=1,
            pixels=b"x" * (_OUTPUT_LIMIT + 1),
        ),
        DecodedRaster(
            width=1,
            height=1,
            pixels=b"xx",
            output_bytes=1,
        ),
    )


class TestDecoderSecurity:
    def test_policy_state(self) -> None:
        policy = _policy()

        assert policy.allow_network is False
        assert policy.allow_model_catalog is False
        assert policy.allow_reference_data is False
        assert policy.allowed_decoder_ids == frozenset((_DECODER_ID,))
        with pytest.raises(AttributeError):
            policy.max_pages = 3  # type: ignore

    @pytest.mark.parametrize(
        "flag",
        ["allow_network", "allow_model_catalog", "allow_reference_data"],
    )
    def test_forbidden_access(self, flag: str) -> None:
        with pytest.raises(DecoderPolicyError):
            _policy(**{flag: True})

    @pytest.mark.parametrize(
        ("policy_field", "invalid_value"),
        [
            ("max_compressed_bytes", 0),
            ("max_width", -1),
            ("max_output_bytes", float("inf")),
            ("allowed_decoder_ids", set()),
            ("allowed_decoder_ids", _DECODER_ID),
        ],
    )
    def test_invalid_limits(
        self, policy_field: str, invalid_value: object
    ) -> None:
        with pytest.raises(DecoderPolicyError):
            _policy(**{policy_field: invalid_value})

    def test_sandbox_input_guards(self) -> None:
        seen: list[bytes] = []
        decoder = Mock(return_value=DecodedRaster(width=1, height=1, pixels=1))
        sandbox = DecoderSandbox(
            _policy(max_compressed_bytes=2),
            _DECODER_ID,
            decoder,
        )

        with pytest.raises(DecoderInputError, match="bytes"):
            sandbox.decode("not bytes")  # type: ignore
        with pytest.raises(DecoderInputError, match="compressed"):
            sandbox.decode(b"123")
        assert seen == []
        assert decoder.call_count == 0

        denied = DecoderSandbox(
            _policy(),
            "unlisted-decoder",
            decoder,
        )
        with pytest.raises(DecoderPolicyError, match="allowlisted"):
            denied.decode(b"ok")
        assert seen == []
        assert decoder.call_count == 0

    def test_sandbox_output_guards(self) -> None:
        sandbox = DecoderSandbox(
            _policy(),
            _DECODER_ID,
            _output_decoder,
        )

        raster_result = sandbox.decode(b"ok")

        assert raster_result.width == 2
        assert raster_result.height == 3
        assert raster_result.output_bytes == len(b"pixels")
        assert raster_result.metadata["mode"] == "L"

        for raster in _invalid_rasters():
            guarded = DecoderSandbox(
                _policy(),
                _DECODER_ID,
                Mock(return_value=raster),
            )
            with pytest.raises(DecoderOutputError):
                guarded.decode(b"ok")

    def test_decoder_exception_is_sanitized(self) -> None:
        payload = b"secret input payload"
        sandbox = DecoderSandbox(_policy(), _DECODER_ID, _failing_decoder)

        with pytest.raises(DecoderSecurityError) as raised:
            sandbox.decode(payload[:2])

        assert str(raised.value) == "decoder invocation failed"
        assert payload not in str(raised.value).encode()
        assert raised.value.__context__ is None
