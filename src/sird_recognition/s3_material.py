"""Read capability-bound objects from an S3-compatible store (SigV4 GET).

The reader uses only the standard library, so the OCR runtime gets no
cloud SDK dependency. It returns bytes only when their SHA-256 matches the
signed capability checksum.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from sird_recognition._runtime_request import RecognitionError
from sird_recognition.codes import TechnicalCode

_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
_ALGORITHM = "AWS4-HMAC-SHA256"
_SERVICE = "s3"
_TERMINATOR = "aws4_request"
_SCHEMES = frozenset(("http", "https"))
_DEFAULT_MAX_BYTES = 20971520
_SERVER_ERROR = 500
_TOO_MANY_REQUESTS = 429


@dataclass(frozen=True, slots=True)
class S3MaterialReader:
    """``MaterialReaderPort`` for one path-style bucket."""

    endpoint: str
    bucket: str
    access_key: str
    secret_key: str = field(repr=False)
    region: str = "us-east-1"
    max_bytes: int = _DEFAULT_MAX_BYTES
    timeout_seconds: float = 30
    clock: Callable[[], datetime] = field(default=lambda: datetime.now(UTC))

    def read(self, artifact_ref: str, *, expected_checksum: str) -> bytes:
        """Return the object bytes; the checksum binds the exact version."""
        # shortcut: no versionId/If-Match pin; the signed SHA-256 already
        # rejects any other version. Pin it when Process sends it to OCR.
        body = self._download(artifact_ref)
        if len(body) > self.max_bytes:
            raise RecognitionError(TechnicalCode.INPUT_LIMIT_EXCEEDED)
        actual = hashlib.sha256(body).hexdigest()
        if not hmac.compare_digest(actual, expected_checksum.lower()):
            raise RecognitionError(TechnicalCode.CAPABILITY_MISMATCH)
        return body

    def _download(self, key: str) -> bytes:
        try:
            with urlopen(  # noqa: S310 - the scheme is checked
                self._signed_request(key), timeout=self.timeout_seconds
            ) as response:
                return response.read(self.max_bytes + 1)
        except HTTPError as error:
            raise RecognitionError(
                TechnicalCode.MATERIAL_UNAVAILABLE,
                retryable=error.code >= _SERVER_ERROR
                or error.code == _TOO_MANY_REQUESTS,
            ) from None
        except (URLError, TimeoutError, OSError):
            raise RecognitionError(
                TechnicalCode.MATERIAL_UNAVAILABLE, retryable=True
            ) from None

    def _signed_request(self, key: str) -> Request:
        base = urlsplit(self.endpoint)
        if base.scheme not in _SCHEMES or not base.netloc:
            raise RecognitionError(TechnicalCode.INVALID_CONFIGURATION)
        prefix = base.path.rstrip("/")
        path = quote(f"{prefix}/{self.bucket}/{key}", safe="/-_.~")
        now = self.clock()
        headers = {
            "host": base.netloc,
            "x-amz-content-sha256": _EMPTY_SHA256,
            "x-amz-date": now.strftime("%Y%m%dT%H%M%SZ"),
        }
        headers["authorization"] = self._authorization(now, path, headers)
        return Request(f"{base.scheme}://{base.netloc}{path}", headers=headers)

    def _authorization(
        self, now: datetime, path: str, headers: Mapping[str, str]
    ) -> str:
        day = now.strftime("%Y%m%d")
        scope = f"{day}/{self.region}/{_SERVICE}/{_TERMINATOR}"
        names = ";".join(headers)
        to_sign = "\n".join(
            (
                _ALGORITHM,
                headers["x-amz-date"],
                scope,
                _sha256_hex(_canonical_request(path, headers)),
            )
        )
        signature = hmac.new(
            self._signing_key(day), to_sign.encode(), hashlib.sha256
        ).hexdigest()
        return (
            f"{_ALGORITHM} Credential={self.access_key}/{scope}, "
            f"SignedHeaders={names}, Signature={signature}"
        )

    def _signing_key(self, day: str) -> bytes:
        signing_key = f"AWS4{self.secret_key}".encode()
        for part in (day, self.region, _SERVICE, _TERMINATOR):
            signing_key = _hmac(signing_key, part)
        return signing_key


def _canonical_request(path: str, headers: Mapping[str, str]) -> str:
    lines = (f"{name}:{header}" for name, header in headers.items())
    return "\n".join(
        ("GET", path, "", *lines, "", ";".join(headers), _EMPTY_SHA256)
    )


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _hmac(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode(), hashlib.sha256).digest()
