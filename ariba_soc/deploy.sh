#!/bin/bash
# Build images, start the stack, wait for health, auto-fix common failures.
set -uo pipefail
cd "$(dirname "$0")"

SERVICES=(db redis web scheduler nginx)
HEALTHCHECKED=(db redis web nginx)   # scheduler has no healthcheck (long-running loop)
MAX_WAIT=180
POLL_INTERVAL=5

log() { echo "==> $*"; }

wait_for_health() {
    local waited=0
    while [ "$waited" -lt "$MAX_WAIT" ]; do
        local all_ok=true
        for svc in "${HEALTHCHECKED[@]}"; do
            cid=$(docker compose ps -q "$svc" 2>/dev/null)
            [ -z "$cid" ] && { all_ok=false; continue; }
            status=$(docker inspect --format '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo "none")
            [ "$status" != "healthy" ] && all_ok=false
        done
        $all_ok && return 0
        sleep "$POLL_INTERVAL"
        waited=$((waited + POLL_INTERVAL))
    done
    return 1
}

failed_services() {
    docker compose ps --format '{{.Service}} {{.State}}' | awk '$2!="running"{print $1}'
}

log "Building images..."
if ! docker compose build; then
    log "Build failed. Aborting."
    exit 1
fi

log "Starting stack..."
docker compose up -d

log "Waiting for services to report healthy (max ${MAX_WAIT}s)..."
if wait_for_health; then
    log "All services healthy."
else
    log "Not all services healthy after ${MAX_WAIT}s. Diagnosing..."

    bad=$(failed_services)
    if [ -n "$bad" ]; then
        for svc in $bad; do
            echo "---- logs: $svc (last 40 lines) ----"
            docker compose logs --tail=40 "$svc"
        done

        log "Auto-fix attempt: re-running migrations + recreating failed services..."
        docker compose exec -T web python manage.py migrate --noinput 2>&1 || true
        # shellcheck disable=SC2086
        docker compose up -d --force-recreate $bad

        log "Re-checking health..."
        if wait_for_health; then
            log "Recovered — all services healthy."
        else
            log "Still unhealthy after auto-fix. Manual investigation needed:"
            docker compose ps
            exit 1
        fi
    else
        log "No exited containers, but healthcheck(s) not passing yet. Current state:"
        docker compose ps
        exit 1
    fi
fi

log "Stack up:"
docker compose ps
