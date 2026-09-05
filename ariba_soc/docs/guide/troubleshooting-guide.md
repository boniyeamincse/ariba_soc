# Troubleshooting Guide

## 1. Wazuh API Connection Fails
**Symptom:** Sync logs show "Failed" and no new alerts appear.
**Fix:** 
- Check `Settings -> Wazuh API Settings`. Ensure credentials are correct.
- Ensure the Ariba SOC server can ping the Wazuh Manager on port 55000.
- If using self-signed certs on Wazuh, disable "Verify SSL Certificate" in settings.

## 2. Static Files Not Loading (Broken UI)
**Symptom:** The platform looks like plain text without CSS.
**Fix:** Run `python manage.py collectstatic`. Ensure your Nginx configuration correctly points to the `staticfiles` directory.

## 3. Cannot Login
**Symptom:** Valid credentials are rejected.
**Fix:** Ensure the database is running. An admin can reset passwords via `Settings -> User Management`.

## 4. Reviewing Audit Logs
For tracing internal errors or unauthorized actions, navigate to `Settings -> Audit Log Settings` or check the main `Audit Logs` view to see exactly who did what, and when.
