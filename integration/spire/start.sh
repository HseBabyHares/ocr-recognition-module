#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repo_root"

compose() {
    docker compose -f integration/spire/compose.yml "$@"
}

integration/spire/init-local-ca.sh

command=${1:-up}
case "$command" in
    up)
        [ "$#" -eq 1 ] || {
            printf '%s\n' 'usage: integration/spire/start.sh [up|down]' >&2
            exit 2
        }
        compose up -d --wait spire-server
        agent_id=spiffe://sird.example/agent/local
        socket=/run/spire/server/api.sock
        workload_id=spiffe://sird.example/workload/spire-probe
        token_json="$(compose exec -T spire-server \
            /opt/spire/bin/spire-server token generate \
            -socketPath "$socket" \
            -spiffeID "$agent_id" \
            -output json)"
        token="$(printf '%s\n' "$token_json" | sed -n \
            's/.*"value"[[:space:]]*:[[:space:]]*"\([^" ]*\)".*/\1/p')"
        [ -n "$token" ] || {
            printf '%s\n' 'SPIRE join token generation returned no token' >&2
            exit 1
        }
        compose exec -T spire-server \
            /opt/spire/bin/spire-server bundle show \
            -socketPath "$socket" -format pem \
            >integration/spire/runtime/bundle.pem
        chmod 600 integration/spire/runtime/bundle.pem

        if ! compose exec -T spire-server \
            /opt/spire/bin/spire-server entry show \
            -socketPath "$socket" -entryID local-spire-probe \
            >/dev/null 2>&1; then
            compose exec -T spire-server \
                /opt/spire/bin/spire-server entry create \
                -socketPath "$socket" \
                -entryID local-spire-probe \
                -spiffeID "$workload_id" \
                -parentID "$agent_id" \
                -selector unix:uid:10001 \
                -selector unix:gid:10001 \
                -selector unix:supplementary_gid:10001 \
                -x509SVIDTTL 300 >/dev/null
        fi

        export SPIRE_JOIN_TOKEN="$token"
        compose up -d --wait spire-agent
        attempt=0
        while ! compose run --rm --no-deps spire-probe; do
            attempt=$((attempt + 1))
            [ "$attempt" -lt 10 ] || {
                printf '%s\n' 'SPIRE workload probe did not receive an SVID' >&2
                exit 1
            }
            sleep 1
        done
        ;;
    down)
        shift
        compose down "$@"
        ;;
    *)
        compose "$@"
        ;;
esac
