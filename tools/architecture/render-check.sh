#!/usr/bin/env bash
set -Eeuo pipefail

blocked() {
  printf 'BLOCKED: %s\n' "$1" >&2
  exit 2
}

require_command() {
  local command_name=$1

  command -v "$command_name" >/dev/null 2>&1 \
    || blocked "$command_name missing"
}

main() {
  local repository_root=${1:-.}
  local output_directory=${2:-artifacts/architecture-render}
  local workspace="$repository_root/architecture/model/workspace.dsl"

  [[ -f "$workspace" ]] || blocked "$workspace missing"

  mkdir -p "$output_directory"
  require_command structurizr-cli
  structurizr-cli validate -workspace "$workspace" \
    >"$output_directory/structurizr-validate.log"

  shopt -s dotglob nullglob globstar
  local candidates=(
    "$repository_root"/architecture/**/*.puml
  )
  local diagrams=()
  local candidate

  for candidate in "${candidates[@]}"; do
    if [[ -f "$candidate" && ! -L "$candidate" ]]; then
      diagrams+=("$candidate")
    fi
  done

  if ((${#diagrams[@]} == 0)); then
    return
  fi

  require_command plantuml

  local diagram
  for diagram in "${diagrams[@]}"; do
    plantuml -checkonly "$diagram"
  done
}

main "$@"
