# Troubleshooting

## Wazuh Connection Issues

### "Invalid credentials" for Manager API

**Symptom:** Test Manager Connection returns "Invalid credentials" or 401.

**Causes & fixes:**
1. Username/password incorrect — verify in `.env` or UI config
2. User lacks required roles — SSH into Wazuh server and check:
   ```bash
   sudo sqlite3 /var/ossec/api/configuration/rbac/rbac.db \
     "SELECT * FROM users WHERE username='soc-api-user';"
   sudo sqlite3 /var/ossec/api/configuration/rbac/rbac.db \
     "SELECT * FROM user_roles WHERE user_id=<id>;"
   ```
3. Assign roles if missing:
   ```bash
   sudo sqlite3 /var/ossec/api/configuration/rbac/rbac.db \
     "INSERT INTO user_roles (user_id, role_id) VALUES (<user_id>, 1);"
   sudo sqlite3 /var/ossec/api/configuration/rbac/rbac.db \
     "INSERT INTO user_roles (user_id, role_id) VALUES (<user_id>, 4);"
   ```
4. Wazuh API not running — check on Wazuh server:
   ```bash
   sudo systemctl status wazuh-api
   sudo journalctl -u wazuh-api -n 50
   ```

### "SSL certificate verify failed"

**Symptom:** Test connection fails with SSL error.

**Fix:** Wazuh uses self-signed certs. The client disables SSL verification by default (`verify=False`). If you need verification, add the Wazuh CA cert and set `verify_ssl=True` in the Indexer config.

### "Connection refused" to Manager/Indexer

**Symptom:** Test connection fails with connection refused.

**Fix:**
1. Check Wazuh server is reachable from Django host:
   ```bash
   ping 10.24.66.2
   curl -k https://10.24.66.2:55000
   curl -k https://10.24.66.2:9200
   ```
2. Check firewall on Wazuh server:
   ```bash
   sudo ufw status
   sudo iptables -L -n
   ```
3. Wazuh services running:
   ```bash
   sudo systemctl status wazuh-manager
   sudo systemctl status wazuh-indexer
   ```

### Indexer "security_exception" or "unauthorized"

**Symptom:** Test Indexer Connection fails with auth error.

**Fix:**
1. Verify user exists:
   ```bash
   curl -k -u admin:password \
     "https://localhost:9200/_plugins/_security/api/internalusers/ariba-soc-reader"
   ```
2. Re-create user with correct role:
   ```bash
   curl -k -u admin:password -X PUT \
     "https://localhost:9200/_plugins/_security/api/internalusers/ariba-soc-reader" \
     -H "Content-Type: application/json" \
     -d '{"password": "AribaS0C_AlertReader!@#", "backend_roles": ["ariba_soc_alert_reader"]}'
   ```
3. Ensure role has correct index permissions:
   ```bash
   curl -k -u admin:password \
     "https://localhost:9200/_plugins/_security/api/roles/ariba_soc_alert_reader"
   ```

## Sync Issues

### "0 alerts fetched" on sync

**Symptom:** Force sync completes but `alerts_fetched=0`.

**Fix:**
1. Check Wazuh has alerts in the time range:
   ```bash
   curl -k -u soc-api-user:password \
     "https://10.24.66.2:55000/security/alerts?limit=1"
   ```
2. The sync uses `since` parameter — clear `last_sync` by creating a fresh config
3. Check sync log for error messages in the detail view

### Duplicate alerts being created

**Symptom:** Same alert appears multiple times.

**Fix:**
1. Check that `wazuh_alert_id` is populated in Wazuh alerts
2. Ensure `alerts_alert.wazuh_alert_id` has a unique constraint (migration 0003 should have this)
3. Run dedup manually:
   ```python
   python manage.py shell -c "
   from alerts.models import Alert
   from django.db.models import Count
   dups = Alert.objects.values('wazuh_alert_id').annotate(
       c=Count('id')).filter(c__gt=1)
   for d in dups:
       Alert.objects.filter(wazuh_alert_id=d['wazuh_alert_id'])\
           .order_by('id')[1:].delete()
   "
   ```

## Application Issues

### 500 Internal Server Error

1. Check Gunicorn logs:
   ```bash
   sudo journalctl -u ariba-soc -n 50 --no-pager
   ```
2. Check Django debug — if `DEBUG=True`, visit the URL that causes the error to see the traceback
3. Check disk space and database connectivity

### 403 Forbidden

1. Check user role — does the user have the correct `AnalystProfile.role`?
2. Ensure `AnalystProfile` exists for the user (signal should auto-create on user creation)
3. Manually create if missing:
   ```python
   python manage.py shell -c "
   from accounts.models import AnalystProfile
   from django.contrib.auth.models import User
   u = User.objects.get(username='username')
   AnalystProfile.objects.get_or_create(user=u, defaults={'role': 'l1_analyst'})
   "
   ```

### "No such table" after migration

**Symptom:** Database errors about missing tables.

**Fix:** Run migrations:
```bash
python manage.py migrate --run-syncdb
python manage.py migrate
```

### Login not working

1. Check user exists: `python manage.py shell -c "from django.contrib.auth.models import User; print(User.objects.filter(is_active=True).count())"`
2. Reset password: `python manage.py changepassword <username>`
3. Check session table isn't corrupted: `python manage.py clearsessions`

## Performance Issues

### Slow dashboard loading

1. Check query count — ensure `select_related` and `prefetch_related` are used in views
2. Database indexing — verify indexes on `alerts_alert(created_at, severity, status)`
3. Add database connection pooling (PGbouncer for PostgreSQL)

### Slow sync operations

1. Reduce `limit` parameter in sync (currently 500)
2. Schedule sync during off-peak hours
3. Monitor Wazuh API response times
