#!/bin/sh
set -e

# Runs the app's periodic management commands on their own interval.
# No cron daemon / root needed — plain loop, runs as the same non-root
# user as the web container.

TICK=${SCHEDULER_TICK_SECONDS:-30}
SYNC_INTERVAL=${WAZUH_SYNC_INTERVAL_SECONDS:-300}
SLA_INTERVAL=${SLA_CHECK_INTERVAL_SECONDS:-120}
CLEANUP_INTERVAL=${CLEANUP_INTERVAL_SECONDS:-86400}
REPORTS_INTERVAL=${REPORTS_INTERVAL_SECONDS:-3600}

last_sync=0
last_sla=0
last_cleanup=0
last_reports=0

while true; do
    now=$(date +%s)

    if [ $((now - last_sync)) -ge "$SYNC_INTERVAL" ]; then
        python manage.py wazuh_sync --time-range 10m || echo "wazuh_sync failed"
        last_sync=$now
    fi

    if [ $((now - last_sla)) -ge "$SLA_INTERVAL" ]; then
        python manage.py check_sla_breaches || echo "check_sla_breaches failed"
        last_sla=$now
    fi

    if [ $((now - last_cleanup)) -ge "$CLEANUP_INTERVAL" ]; then
        python manage.py cleanup_audit_logs || echo "cleanup_audit_logs failed"
        last_cleanup=$now
    fi

    if [ $((now - last_reports)) -ge "$REPORTS_INTERVAL" ]; then
        python manage.py generate_reports || echo "generate_reports failed"
        last_reports=$now
    fi

    sleep "$TICK"
done
