#!/bin/sh
set -eu

runtime_dir=${1:-integration/spire/runtime}
mkdir -p "$runtime_dir"
umask 077

if [ -s "$runtime_dir/upstream-ca.key" ] &&
    [ -s "$runtime_dir/upstream-ca.crt" ]; then
    exit 0
fi

command -v openssl >/dev/null 2>&1 || {
    printf '%s\n' 'openssl is required to initialize local SPIRE state' >&2
    exit 1
}

rm -f "$runtime_dir/upstream-ca.key" "$runtime_dir/upstream-ca.crt"
openssl req -x509 -newkey rsa:3072 -nodes -days 7 \
    -keyout "$runtime_dir/upstream-ca.key" \
    -out "$runtime_dir/upstream-ca.crt" \
    -subj '/CN=sird-local-spire-upstream-ca' \
    -addext 'basicConstraints=critical,CA:TRUE,pathlen:1' \
    -addext 'keyUsage=critical,keyCertSign,cRLSign' \
    -addext 'subjectKeyIdentifier=hash' >/dev/null 2>&1
chmod 600 "$runtime_dir/upstream-ca.key" "$runtime_dir/upstream-ca.crt"
