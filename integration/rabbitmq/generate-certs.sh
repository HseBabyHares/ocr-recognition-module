#!/usr/bin/env bash
set -euo pipefail

output_dir="${1:-integration/certs/rabbitmq}"
mkdir -p "$output_dir"
umask 077
for tool in openssl chmod mkdir mv; do
  command -v "$tool" >/dev/null 2>&1 || {
    printf 'Required tool not found: %s\n' "$tool" >&2
    exit 1
  }
done

files=(ca.crt ca.key server.crt server.key client.crt client.key)
present=0
missing=0
for file in "${files[@]}"; do
  if [[ -f "$output_dir/$file" ]]; then
    present=$((present + 1))
  else
    missing=$((missing + 1))
  fi
done
if (( present > 0 && missing > 0 )); then
  printf 'Refusing to overwrite partial RabbitMQ certificate set in %s\n' "$output_dir" >&2
  exit 1
fi
if (( present == ${#files[@]} )); then
  chmod 0644 "$output_dir/ca.crt" "$output_dir/server.crt" "$output_dir/server.key"
  chmod 0600 "$output_dir/ca.key" "$output_dir/client.key"
  printf 'RabbitMQ TLS material already exists in %s\n' "$output_dir"
  exit 0
fi

work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout "$work_dir/ca.key" -out "$work_dir/ca.crt" \
  -subj "/CN=sird-integration-ca" \
  -addext "basicConstraints=critical,CA:TRUE,pathlen:1" \
  -addext "keyUsage=critical,keyCertSign,cRLSign" \
  -addext "subjectKeyIdentifier=hash"

openssl req -newkey rsa:2048 -nodes \
  -keyout "$work_dir/server.key" -out "$work_dir/server.csr" \
  -subj "/CN=rabbitmq"
printf 'subjectAltName=DNS:rabbitmq,DNS:localhost,IP:127.0.0.1\n' >"$work_dir/server.ext"
openssl x509 -req -days 365 -in "$work_dir/server.csr" \
  -CA "$work_dir/ca.crt" -CAkey "$work_dir/ca.key" -CAcreateserial \
  -out "$work_dir/server.crt" -extfile "$work_dir/server.ext"

openssl req -newkey rsa:2048 -nodes \
  -keyout "$work_dir/client.key" -out "$work_dir/client.csr" \
  -subj "/CN=sird-process"
printf 'extendedKeyUsage=clientAuth\n' >"$work_dir/client.ext"
openssl x509 -req -days 365 -in "$work_dir/client.csr" \
  -CA "$work_dir/ca.crt" -CAkey "$work_dir/ca.key" -CAcreateserial \
  -out "$work_dir/client.crt" -extfile "$work_dir/client.ext"

for file in "${files[@]}"; do
  mv "$work_dir/$file" "$output_dir/$file"
done
chmod 0644 "$output_dir/ca.crt" "$output_dir/server.crt" "$output_dir/server.key"
chmod 0600 "$output_dir/ca.key" "$output_dir/client.key"
printf 'Generated RabbitMQ TLS material in %s\n' "$output_dir"
