"""gRPC entry point for the SNILS OCR service (``sird-ocr-server``).

Environment:
  SIRD_OCR_LISTEN             bind address, default ``[::]:50051``
  SIRD_OCR_MAX_WORKERS        concurrent calls, default 4
  SIRD_OCR_POLICY_ID          optional; the only accepted input policy id
  SIRD_OCR_TLS_CERT/KEY/CLIENT_CA  all three enable mTLS; none = plaintext
  CAPABILITY_KEYS             ``kid:hex[,kid:hex]`` shared with Process
  CAPABILITY_ISSUER           expected ``issuer`` claim
  CAPABILITY_AUDIENCE         expected ``audience`` claim
  S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, S3_REGION
  SIRD_TESSERACT_SHA256, SIRD_TESSDATA_SHA256  optional checksum pins
  OTEL_EXPORTER_OTLP_[METRICS_]ENDPOINT  optional; enables OTLP/HTTP metrics
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import grpc

from sird_recognition._ocr_composition import build_runtime
from sird_recognition.grpc_adapter import register_ocr_service
from sird_recognition.runtime import RecognizerRuntime
from sird_recognition.telemetry import configure_metrics

_TLS_NAMES = ("CERT", "KEY", "CLIENT_CA")


def serve(
    runtime: RecognizerRuntime, address: str, workers: int
) -> tuple[grpc.Server, int]:
    """Start a synchronous gRPC server; return it and the bound port."""
    server = grpc.server(ThreadPoolExecutor(max_workers=workers))
    register_ocr_service(server, runtime)
    port = _bind(server, address)
    server.start()
    return server, port


def main() -> None:
    """Serve until the process gets a termination signal."""
    configure_metrics()
    server, _ = serve(
        build_runtime(),
        os.environ.get("SIRD_OCR_LISTEN", "[::]:50051"),
        int(os.environ.get("SIRD_OCR_MAX_WORKERS", "4")),
    )
    server.wait_for_termination()


def _bind(server: grpc.Server, address: str) -> int:
    paths = [os.environ.get(f"SIRD_OCR_TLS_{name}") for name in _TLS_NAMES]
    if not any(paths):
        return server.add_insecure_port(address)
    if not all(paths):
        raise RuntimeError("SIRD_OCR_TLS_CERT, KEY and CLIENT_CA go together")
    cert, key, client_ca = (_read(path) for path in paths)
    credentials = grpc.ssl_server_credentials(
        [(key, cert)], root_certificates=client_ca, require_client_auth=True
    )
    return server.add_secure_port(address, credentials)


def _read(path: str | None) -> bytes:
    return Path(str(path)).read_bytes()


if __name__ == "__main__":
    main()
