#!/usr/bin/env python3
"""Minimal LSP adapter that runs flake8 with WPS rules per opened Python file.

OMP configures flake8 as a custom linter server, but flake8 is a CLI tool,
not an LSP server. This adapter speaks the small LSP subset OMP's linter
client uses (initialize, didOpen/didSave) and publishes parsed flake8
diagnostics back to the client.

Excluded from repository lint gates via `# flake8: noqa: WPS`.
"""
# flake8: noqa: WPS

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

MAX_HEADER = 16384
SEVERITY = {"E": "Error", "W": "Warning", "F": "Fatal", "C": "Error"}


def _read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line or len(line) > MAX_HEADER:
            return None
        if line in (b"\r\n", b"\n"):
            break
        name, _, value = line.partition(b":")
        headers[name.decode("ascii").lower()] = value.strip().decode("ascii")
    length = int(headers.get("content-length", "0"))
    if length <= 0 or length > 4 * 1024 * 1024:
        return None
    body = sys.stdin.buffer.read(length)
    return json.loads(body)


def _send(message: dict[str, Any]) -> None:
    payload = json.dumps(message).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(payload)}\r\n\r\n".encode())
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def _run_flake8(
    file_path: str,
    cwd: str,
    source_text: str | None = None,
) -> list[dict[str, Any]]:
    if not file_path.startswith("file://"):
        return []
    try:
        from urllib.parse import unquote, urlparse

        local_path = Path(unquote(urlparse(file_path).path))
    except Exception:
        return []
    if not local_path.name.endswith(".py"):
        return []
    if source_text is None and not local_path.is_file():
        return []
    command = ["flake8", "--format", "default"]
    input_text: str | None = None
    if source_text is None:
        command.append(str(local_path))
    else:
        command.extend(["--stdin-display-name", str(local_path), "-"])
        input_text = source_text
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            input=input_text,
            text=True,
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        return []
    except FileNotFoundError:
        return []
    diagnostics: list[dict[str, Any]] = []
    for raw_line in result.stdout.splitlines():
        parts = raw_line.split(":", 3)
        if len(parts) < 4:
            continue
        try:
            line = int(parts[1])
        except ValueError:
            continue
        try:
            column = int(parts[2])
        except ValueError:
            column = 1
        code = parts[3].split(" ", 1)[0]
        severity = SEVERITY.get(code[:1], "Warning")
        message = parts[3]
        diagnostics.append(
            {
                "range": {
                    "start": {
                        "line": line - 1,
                        "character": max(column - 1, 0),
                    },
                    "end": {
                        "line": line - 1,
                        "character": max(column - 1, 0) + 1,
                    },
                },
                "severity": {
                    "Error": 1,
                    "Warning": 2,
                    "Hint": 4,
                }.get(severity, 2),
                "code": code,
                "source": "flake8",
                "message": message,
            }
        )
    return diagnostics


def _publish_diagnostics(
    uri: str,
    diagnostics: list[dict[str, Any]],
) -> None:
    _send(
        {
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {"uri": uri, "diagnostics": diagnostics},
        }
    )


def main() -> int:
    server_capabilities: dict[str, Any] = {
        "textDocumentSync": 1,
    }
    pending: dict[str, str] = {}
    while True:
        message = _read_message()
        if message is None:
            return 0
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") or {}

        if method == "initialize":
            pending.clear()
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"capabilities": server_capabilities},
                }
            )
            continue

        if method == "initialized":
            continue

        if method == "shutdown":
            if request_id is not None:
                _send({"jsonrpc": "2.0", "id": request_id, "result": None})
            continue

        if method == "exit":
            return 0

        if method == "textDocument/didOpen":
            text_document = params.get("textDocument") or {}
            uri = text_document.get("uri", "")
            source_text = text_document.get("text") or ""
            pending[uri] = source_text
            _publish_diagnostics(
                uri,
                _run_flake8(uri, os.getcwd(), source_text),
            )
            continue

        if method == "textDocument/didChange":
            text_document = params.get("textDocument") or {}
            uri = text_document.get("uri", "")
            content_changes = params.get("contentChanges") or []
            if content_changes and isinstance(content_changes[-1], dict):
                source_text = content_changes[-1].get("text") or ""
                pending[uri] = source_text
                _publish_diagnostics(
                    uri,
                    _run_flake8(uri, os.getcwd(), source_text),
                )
            continue

        if method == "textDocument/didSave":
            text_document = params.get("textDocument") or {}
            uri = text_document.get("uri", "")
            source_text = pending.get(uri)
            _publish_diagnostics(
                uri,
                _run_flake8(uri, os.getcwd(), source_text),
            )
            continue

        if method == "textDocument/didClose":
            pending.pop(params.get("textDocument", {}).get("uri", ""), None)
            continue

        if (
            request_id is not None
            and isinstance(request_id, (int, str))
            and method is not None
        ):
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"method not found: {method}",
                    },
                }
            )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0) from None
