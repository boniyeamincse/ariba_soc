#!/bin/sh
set -e

# Runs the app's periodic management commands on their own interval.
# No cron daemon / root needed — plain loop, runs as the same non-root
# user as the web container.

SYNC_INTERVAL=${WAZUH_SYNC_INTERVAL_SECONDS:-300}
CLEANUP_INTERVAL=${CLEANUP_INTERVAL_SECONDS:-86400}
REPORTS_INTERVAL=${REPORTS_INTERVAL_SECONDS:-3600}

last_cleanup=0
last_reports=0

while true; do
    now=$(date +%s)

    python manage.py wazuh_sync --time-range 10m || echo "wazuh_sync failed"

    if [ $((now - last_cleanup)) -ge "$CLEANUP_INTERVAL" ]; then
        python manage.py cleanup_audit_logs || echo "cleanup_audit_logs failed"
        last_cleanup=$now
    fi

    if [ $((now - last_reports)) -ge "$REPORTS_INTERVAL" ]; then
        python manage.py generate_reports || echo "generate_reports failed"
        last_reports=$now
    fi

    sleep "$SYNC_INTERVAL"
done
