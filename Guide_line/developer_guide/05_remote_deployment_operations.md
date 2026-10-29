# 💻 Developer Guide: 05. Remote Deployment & Server Operations

## 1. Zero Source Code Exposure Philosophy
Ariba SOC follows strict intellectual property and security best practices:
- **No Python/Django source code is ever sent to or stored on remote production servers.**
- The production server receives only Docker configurations, SSL certs, and orchestration scripts from the `remoted/` directory.
- Application code runs strictly inside compiled, immutable Docker images pulled from Docker Hub (`boniyeamin/ariba_soc-*`).

---

## 2. Remote Server Initial Setup
From the local development machine:
```bash
./deploy-remote.sh <USER>@<SERVER_IP>
```
This transfers `remoted/` to `~/ariba_soc_deploy` on the remote server.

Then SSH into the server:
```bash
ssh <USER>@<SERVER_IP>
cd ~/ariba_soc_deploy
cp .env.example .env
nano .env # configure production secrets
./scripts/setup.sh
```

---

## 3. Remote Server Updating Procedure
When a new version is built and pushed to Docker Hub:
```bash
# On the remote server:
cd ~/ariba_soc_deploy
echo "<PASSWORD>" | sudo -S docker compose -p infrastructure pull web scheduler
echo "<PASSWORD>" | sudo -S docker compose -p infrastructure up -d --no-deps web scheduler
```

### Applying Database Reparsing on Remote:
```bash
echo "<PASSWORD>" | sudo -S docker exec infrastructure-web-1 python manage.py reparse_wazuh_alerts
```
