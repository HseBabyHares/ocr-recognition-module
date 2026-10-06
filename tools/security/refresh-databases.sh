#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CACHE_DIR="${SECURITY_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/omp-fadd/security}"
python3 "$ROOT/tools/security/preflight.py" --strict
mkdir -p "$CACHE_DIR/trivy" "$CACHE_DIR/osv"
trivy --cache-dir "$CACHE_DIR/trivy" image --download-db-only
trivy --cache-dir "$CACHE_DIR/trivy" image --download-java-db-only
OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY="$CACHE_DIR/osv" \
  osv-scanner --offline-vulnerabilities --download-offline-databases "$CACHE_DIR/osv"
python3 - "$CACHE_DIR/metadata.json" "$ROOT/tools/security/toolchain.lock.json" <<'PY'
import datetime
import hashlib
import json
import pathlib
import sys

lock_path = pathlib.Path(sys.argv[2])
output_path = pathlib.Path(sys.argv[1])
metadata = {
    "schemaVersion": "1.0",
    "updatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "toolchainSha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
    "databases": [
        "trivy-vulnerability",
        "trivy-java",
        "osv-offline",
    ],
}
text = json.dumps(metadata, indent=2) + "\n"
output_path.write_text(text)
print(text, end="")
PY
