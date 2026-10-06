#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec uv run --directory "$ROOT_DIR" granian \
  --interface asgi \
  --host "${SIRD_HOST:-127.0.0.1}" \
  --port "${SIRD_PORT:-8000}" \
  sird_test_app.local_snils:app
