#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

compose_file="$repo_root/compose.integration.yml"
env_file="$repo_root/integration/.env"
[[ -f "$compose_file" ]] || { printf 'Missing %s\n' "$compose_file" >&2; exit 1; }
[[ -f "$env_file" ]] || {
  printf 'Missing %s; copy integration/.env.example before starting\n' "$env_file" >&2
  exit 1
}
command -v docker >/dev/null 2>&1 || {
  printf 'Required tool not found: docker\n' >&2
  exit 1
}

rabbitmq_password=''
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%$'\r'}"
  [[ -z "$line" || "$line" == \#* ]] && continue
  [[ "$line" == *=* ]] || {
    printf 'Only plain KEY=VALUE syntax is supported in %s\n' "$env_file" >&2
    exit 1
  }
  key="${line%%=*}"
  value="${line#*=}"
  [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || {
    printf 'Unsupported syntax in %s\n' "$env_file" >&2
    exit 1
  }
  if [[ "$value" == *"'"* || "$value" == *'"'* || "$value" == *'\\'* ||
        "$value" == *'$'* || "$value" == *'`'* ]]; then
    printf 'Only plain KEY=VALUE syntax is supported in %s\n' "$env_file" >&2
    exit 1
  fi
  if [[ "$key" == RABBITMQ_PASSWORD ]]; then
    [[ -z "$rabbitmq_password" ]] || {
      printf 'Duplicate RABBITMQ_PASSWORD in %s\n' "$env_file" >&2
      exit 1
    }
    rabbitmq_password="$value"
  fi
done <"$env_file"
[[ -n "$rabbitmq_password" ]] || {
  printf 'RABBITMQ_PASSWORD is required in %s\n' "$env_file" >&2
  exit 1
}

integration/rabbitmq/generate-certs.sh
compose=(docker compose --env-file "$env_file" -f "$compose_file")
"${compose[@]}" up -d --wait
if ! "${compose[@]}" exec -T rabbitmq rabbitmqctl add_user sird "$rabbitmq_password" >/dev/null 2>&1; then
  "${compose[@]}" exec -T rabbitmq rabbitmqctl change_password sird "$rabbitmq_password" >/dev/null
fi
"${compose[@]}" exec -T rabbitmq rabbitmqctl set_permissions -p /sird sird ".*" ".*" ".*" >/dev/null
printf 'Integration services are healthy and RabbitMQ topology is loaded.\n'
