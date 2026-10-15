"""A local S3 stand-in that serves one synthetic object."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from sird_recognition.s3_material import S3MaterialReader
from tests._ocr_fixtures import IMAGE, OBJECT_ID

BUCKET = "bucket"


def reader(endpoint: str) -> S3MaterialReader:
    """Return a reader for the synthetic bucket."""
    return S3MaterialReader(endpoint, BUCKET, "access", "secret")


@contextmanager
def object_store() -> Iterator[str]:
    """Serve ``IMAGE`` at ``/bucket/objects/1`` and yield the endpoint."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), ObjectStore)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


class ObjectStore(BaseHTTPRequestHandler):
    """Answer one known object; record the last authorization header."""

    authorization = ""

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        """Return the object or 404."""
        ObjectStore.authorization = self.headers.get("Authorization", "")
        found = self.path == f"/{BUCKET}/{OBJECT_ID}"
        self.send_response(HTTPStatus.OK if found else HTTPStatus.NOT_FOUND)
        self.end_headers()
        if found:
            self.wfile.write(IMAGE)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Keep the test output quiet."""
