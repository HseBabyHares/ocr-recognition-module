"""Validation helpers for asynchronous SNILS image uploads."""

from __future__ import annotations

from typing import Any

from litestar import Response
from litestar.datastructures import UploadFile

from sird_test_app import _http_helpers
from sird_test_app._app_types import SnilsUpload

UPLOAD_DESCRIPTION = "SNILS image to process asynchronously."
UPLOAD_SIZE_MIB = 15
MAX_UPLOAD_BYTES = UPLOAD_SIZE_MIB * 1024 * 1024
MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES + 1024 * 1024
ALLOWED_IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp", "image/tiff")


def invalid_upload(diagnostic: str, *, status_code: int) -> Response[Any]:
    """Build a consistent upload refusal response."""
    return _http_helpers._upload_refusal(
        (diagnostic,), status_code=status_code
    )


async def read_upload(upload_data: SnilsUpload) -> bytes | Response[Any]:
    """Validate and read one uploaded image."""
    upload = upload_data.file
    if not isinstance(upload, UploadFile):
        return invalid_upload(
            "image_file_required", status_code=_http_helpers.HTTP_BAD_REQUEST
        )
    content_type = (upload.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        return invalid_upload(
            "unsupported_image_type",
            status_code=_http_helpers.HTTP_BAD_REQUEST,
        )
    return await _read_upload_bytes(upload)


async def _read_upload_bytes(upload: UploadFile) -> bytes | Response[Any]:
    try:
        image_bytes = await upload.read()
    except (OSError, ValueError):
        return invalid_upload(
            "image_read_failed", status_code=_http_helpers.HTTP_BAD_REQUEST
        )
    if not image_bytes:
        return invalid_upload(
            "empty_image", status_code=_http_helpers.HTTP_BAD_REQUEST
        )
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        return invalid_upload(
            "image_too_large", status_code=_http_helpers.HTTP_REQUEST_TOO_LARGE
        )
    return image_bytes
