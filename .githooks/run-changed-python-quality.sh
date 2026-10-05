#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"

mapfile -t changed_files < <(
  git -C "$repo_root" diff --cached --name-only --diff-filter=ACMR -- '*.py'
)

if (( ${#changed_files[@]} == 0 )); then
  exit 0
fi

for project_root in "." "integration"; do
  project_files=()
  for candidate in "${changed_files[@]}"; do
    if [[ "$project_root" == "." ]]; then
      if [[ "$candidate" != integration/* ]]; then
        project_files+=("$candidate")
      fi
    elif [[ "$candidate" == integration/* ]]; then
      project_files+=("${candidate#integration/}")
    fi
  done
  if (( ${#project_files[@]} == 0 )); then
    continue
  fi

  absolute_root="$repo_root/$project_root"
  printf 'Checking %s (%d Python file(s))...\n' \
    "$project_root" "${#project_files[@]}"
  (
    cd "$absolute_root"
    uv run --project . --group dev ruff format --check "${project_files[@]}"
    uv run --project . --group dev ruff check "${project_files[@]}"
    ty check "${project_files[@]}"
    flake8 --select=WPS,E999 "${project_files[@]}"
  ) || exit 1
done