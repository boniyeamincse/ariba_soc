# Ariba SOC Unified Security Stack

Welcome to the **Ariba SOC Unified Security Stack**. This project provides a fully containerized, end-to-end security operations center environment built using Docker Compose. It integrates the custom **Ariba SOC** dashboard with a single-node **Wazuh** ecosystem (Manager, Indexer, and Dashboard).

The Ariba SOC dashboard automatically synchronizes alerts from the Wazuh Indexer every 5 minutes, providing a centralized and customized pane of glass for security analysts.

---

## Directory Structure

- **`ariba_soc/`**: Contains the Django-based Ariba SOC web application, database configuration, and synchronization schedulers.
- **`infrastructure/`**: The root of the unified Docker Compose stack. Contains all routing configurations, Wazuh certificates, and operational scripts.

---

## Prerequisites

Before starting the stack, your Linux host system must meet the memory map requirements for OpenSearch (used by Wazuh Indexer).

Run the following command on your host machine:
```bash
sudo sysctl -w vm.max_map_count=262144
```
*(To make this permanent, add `vm.max_map_count=262144` to `/etc/sysctl.conf`)*

---

## Getting Started

All administrative tasks are handled via automated scripts located in `infrastructure/scripts/`.

To boot up the entire stack, generate the necessary TLS certificates, and automatically seed the database configurations, simply run:

```bash
cd infrastructure
./scripts/setup.sh
```

**Services and Ports:**
Once the stack is running, you can access the interfaces locally:
- **Ariba SOC Dashboard**: [http://localhost](http://localhost) (Port 80)
- **Wazuh Dashboard**: [https://localhost](https://localhost) (Port 443)
- **Wazuh Manager APIs/Agents**: Ports `1514`, `1515`, `514/udp`, `55000`

---

## Operational Scripts

The `infrastructure/scripts/` directory provides easy-to-use tools for managing the lifecycle of your SOC stack.

### 1. Health Check
Quickly verify the status of all Docker containers and internal API connectivity.
```bash
./scripts/health-check.sh
```

### 2. Backup
Securely exports a `.sql` dump of the Ariba SOC PostgreSQL database and archives the Wazuh configurations (`config/` folder). The backups are stored in a timestamped folder inside `infrastructure/backups/`.
```bash
./scripts/backup.sh
```

### 3. Restore
Restores the database and Wazuh configurations from a specific backup timestamp. *Warning: This is a destructive action that overwrites the current active state.*
```bash
./scripts/restore.sh <TIMESTAMP>
# Example: ./scripts/restore.sh 20260812_002800
```
