"""Fail-closed local certificate material checks for RabbitMQ mTLS clients.

This module validates local files only. It does not issue certificates or
implement SPIFFE/SPIRE workload identity.
"""

from __future__ import annotations

import os
import ssl
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, cast
from urllib.parse import urlsplit

_PRIVATE_KEY_MODE = 0o600


class TlsConfigurationError(ValueError):
    """TLS certificate material or transport settings are invalid."""


def _raise_tls_error(
    message: str,
    cause: BaseException | None = None,
) -> NoReturn:
    error = TlsConfigurationError(message)
    if cause is None:
        raise error
    raise error from cause


def _local_path(candidate: object, field_name: str) -> Path:
    try:
        raw_path = os.fspath(
            cast(
                str | bytes | os.PathLike[str] | os.PathLike[bytes],
                candidate,
            )
        )
    except TypeError as exc:
        _raise_tls_error(
            f"{field_name} must be a local file path",
            exc,
        )
    if isinstance(raw_path, bytes):
        _raise_tls_error(f"{field_name} must be a local file path")
    path_value = raw_path.strip()
    if not path_value:
        _raise_tls_error(f"{field_name} must be a non-empty path")
    try:
        parsed = urlsplit(path_value)
    except ValueError as exc:
        _raise_tls_error(
            f"{field_name} must be a local file path",
            exc,
        )
    if parsed.scheme or parsed.netloc or "://" in path_value:
        _raise_tls_error(f"{field_name} must not be a URL")
    return Path(path_value)


def _local_file(candidate: object, field_name: str) -> str:
    path = _local_path(candidate, field_name)
    try:
        is_regular = path.is_file() and stat.S_ISREG(path.stat().st_mode)
    except OSError as exc:
        raise TlsConfigurationError(
            f"{field_name} must be an existing regular file"
        ) from exc
    if not is_regular:
        raise TlsConfigurationError(
            f"{field_name} must be an existing regular file"
        )
    return str(path)


def _private_key_file(candidate: object) -> str:
    path_value = _local_file(candidate, "private_key")
    try:
        mode = stat.S_IMODE(Path(path_value).stat().st_mode)
    except OSError as exc:
        raise TlsConfigurationError(
            "private_key must be readable by its owner"
        ) from exc
    if mode & ~_PRIVATE_KEY_MODE or not mode & stat.S_IRUSR:
        raise TlsConfigurationError(
            "private_key permissions must be 0600 or stricter"
        )
    return path_value


@dataclass(frozen=True, slots=True)
class TlsClientIdentity:
    """Local CA, client certificate, and private key file paths."""

    ca_cert: str
    client_cert: str
    private_key: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "ca_cert", _local_file(self.ca_cert, "ca_cert")
        )
        object.__setattr__(
            self, "client_cert", _local_file(self.client_cert, "client_cert")
        )
        object.__setattr__(
            self, "private_key", _private_key_file(self.private_key)
        )

    @property
    def ca_certificate(self) -> str:
        """Compatibility name for the CA certificate path."""
        return self.ca_cert

    @property
    def client_certificate(self) -> str:
        """Compatibility name for the client certificate path."""
        return self.client_cert


def tls_ssl_context(
    identity: TlsClientIdentity,
    *,
    server_hostname: str | None = None,
) -> ssl.SSLContext:
    """Build a verified client context for an AMQPS connection."""
    if not isinstance(identity, TlsClientIdentity):
        raise TypeError("identity must be a TlsClientIdentity")
    context = ssl.create_default_context(cafile=identity.ca_cert)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    try:
        context.load_cert_chain(identity.client_cert, identity.private_key)
    except (OSError, ssl.SSLError) as exc:
        raise TlsConfigurationError(
            "client certificate chain is invalid"
        ) from exc
    if server_hostname is not None and not server_hostname.strip():
        raise TlsConfigurationError("server_hostname must not be empty")
    return context
