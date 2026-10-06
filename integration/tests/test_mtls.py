from __future__ import annotations

import os
from pathlib import Path

import pytest
from sird_workflow.mtls import TlsClientIdentity, TlsConfigurationError

SECURE_MODE = 0o600
READ_ONLY_MODE = 0o400
INSECURE_MODE = 0o640


def _identity(tmp_path: Path) -> TlsClientIdentity:
    ca = tmp_path / "ca.crt"
    cert = tmp_path / "client.crt"
    key = tmp_path / "client.key"
    for path in (ca, cert, key):
        path.write_text("certificate material")
        path.chmod(SECURE_MODE)
    return TlsClientIdentity(str(ca), str(cert), str(key))


def test_identity_requires_secure_local_files(
    tmp_path: Path,
) -> None:
    identity = _identity(tmp_path)
    assert identity.ca_certificate == str(tmp_path / "ca.crt")
    assert identity.client_certificate == str(tmp_path / "client.crt")

    with pytest.raises(TlsConfigurationError, match="existing regular file"):
        TlsClientIdentity(
            str(tmp_path / "missing"),
            identity.client_cert,
            identity.private_key,
        )

    os.chmod(identity.private_key, INSECURE_MODE)
    with pytest.raises(TlsConfigurationError, match="0600"):
        TlsClientIdentity(
            identity.ca_cert, identity.client_cert, identity.private_key
        )
    os.chmod(identity.private_key, READ_ONLY_MODE)
    assert identity.private_key.endswith("client.key")


@pytest.mark.parametrize(
    "path", ["", "https://example.test/ca.crt", "file:///tmp/ca.crt"]
)
def test_identity_rejects_empty_and_url_paths(
    tmp_path: Path, path: str
) -> None:
    identity = _identity(tmp_path)
    with pytest.raises(TlsConfigurationError):
        TlsClientIdentity(path, identity.client_cert, identity.private_key)
