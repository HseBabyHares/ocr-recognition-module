#!/usr/bin/env bash
set -Eeuo pipefail
for cmd in actionlint shellcheck check-jsonschema zizmor; do command -v "$cmd" >/dev/null || { echo "BLOCKED: $cmd missing" >&2; exit 2; }; done
actionlint -no-color
mapfile -d '' shells < <(find . -type f -name '*.sh' -not -path './.git/*' -print0);((${#shells[@]}==0)) || shellcheck -x "${shells[@]}"
for f in .github/workflows/*.yml .github/workflows/*.yaml; do [[ -f "$f" ]] && check-jsonschema --builtin-schema vendor.github-actions "$f"; done
zizmor --pedantic .
