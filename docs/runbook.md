# Incident Runbook

## Table of Contents
1. [Service Down](#service-down)
2. [Database Connection Lost](#database-connection-lost)
3. [Wazuh Sync Failed](#wazuh-sync-failed)
4. [High Memory Usage](#high-memory-usage)
5. [Disk Space Critical](#disk-space-critical)
6. [Security Breach](#security-breach)

---

## Service Down

### Symptoms
- Dashboard not loading
- Health check failing
- Users reporting 502/503 errors

### Diagnosis
```bash
# Check container status
docker compose ps

# Check service logs
docker compose logs web --tail=50

# Check resource usage
docker stats
```

### Resolution
```bash
# Restart specific service
docker compose restart web

# Full stack restart
docker compose down && docker compose up -d

# If persistent, rebuild
docker compose up -d --build --force-recreate web
```

---

## Database Connection Lost

### Symptoms
- "OperationalError: could not connect to server"
- Application errors on login
- Scheduler failing

### Diagnosis
```bash
# Check PostgreSQL status
docker compose exec db pg_isready

# Check connections
docker compose exec db psql -U ariba_soc -c "SELECT count(*) FROM pg_stat_activity;"

# Check logs
docker compose logs db --tail=50
```

### Resolution
```bash
# Restart database
docker compose restart db

# If corrupted, restore from backup
make restore TIMESTAMP=<latest_backup>

# Check disk space (common cause)
df -h
```

---

## Wazuh Sync Failed

### Symptoms
- No new alerts appearing
- Sync logs showing "Failed"
- Scheduler errors

### Diagnosis
```bash
# Check scheduler logs
docker compose logs scheduler --tail=50

# Test indexer connection
docker compose exec web python -c "
from wazuh_integration.services import IndexerClient
from wazuh_integration.models import WazuhConfiguration
config = WazuhConfiguration.objects.first()
client = IndexerClient(config)
print(client.test_connection())
"

# Manual sync attempt
docker compose exec web python manage.py wazuh_sync --time-range 1h
```

### Resolution
```bash
# Check Wazuh Indexer health
curl -k -u admin:password https://localhost:9200/_cluster/health

# Re-seed configuration
docker compose exec web python seed_wazuh_config.py

# Restart scheduler
docker compose restart scheduler
```

---

## High Memory Usage

### Symptoms
- Containers being OOM killed
- Slow response times
- Swap usage high

### Diagnosis
```bash
# Check memory usage
docker stats --format "table {{.Name}}\t{{.MemUsage}}"

# Check system memory
free -h

# Check for memory-hungry processes
ps aux --sort=-%mem | head -10
```

### Resolution
```bash
# Reduce Wazuh Indexer memory (edit docker-compose.yml)
# Change: OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g
# To: OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m

# Reduce Gunicorn workers (edit Dockerfile)
# Change: --workers 4
# To: --workers 2

# Restart affected services
docker compose up -d --force-recreate web wazuh.indexer
```

---

## Disk Space Critical

### Symptoms
- "No space left on device" errors
- Containers failing to start
- Database write errors

### Diagnosis
```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Find large files
du -sh /* | sort -rh | head -10
```

### Resolution
```bash
# Clean Docker resources
docker system prune -f

# Clean old backups
ls -la infrastructure/backups/
rm infrastructure/backups/old_backup_*

# Clean old logs
docker compose logs --tail=0

# Vacuum PostgreSQL
docker compose exec db psql -U ariba_soc -c "VACUUM FULL;"
```

---

## Security Breach

### Symptoms
- Unauthorized access attempts
- Suspicious activity in audit logs
- Unexpected configuration changes

### Immediate Actions
```bash
# 1. Check audit logs
docker compose exec web python manage.py shell -c "
from audit.models import AuditLog
logs = AuditLog.objects.order_by('-created_at')[:100]
for log in logs:
    print(f'{log.created_at} - {log.user} - {log.action} - {log.resource}')
"

# 2. Check for unauthorized users
docker compose exec web python manage.py shell -c "
from django.contrib.auth.models import User
for u in User.objects.filter(is_active=True):
    print(f'{u.username} - {u.email} - Last login: {u.last_login}')
"

# 3. Rotate secrets immediately
# Edit .env with new secrets
# Recreate containers
docker compose up -d --force-recreate
```

### Post-Incident
1. Document timeline of events
2. Review and update access controls
3. Consider enabling 2FA
4. Update SECURITY.md with lessons learned

---

## Escalation Matrix

| Severity | Response Time | Escalation |
|----------|--------------|------------|
| P0 (Critical) | 15 minutes | SOC L3 → Manager → CISO |
| P1 (High) | 1 hour | SOC L2 → SOC L3 |
| P2 (Medium) | 4 hours | SOC L1 → SOC L2 |
| P3 (Low) | 24 hours | SOC L1 |

## Contact Information

| Role | Contact |
|------|---------|
| SOC Manager | boniyeamin.cse1@gmail.com |
| On-Call Engineer | [Rotating] |
| Emergency | [Phone] |

---

*Last updated: 2026-09-05*
