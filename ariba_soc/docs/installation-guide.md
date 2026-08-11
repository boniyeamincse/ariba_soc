# Installation Guide

## Prerequisites

- **Python 3.10+**
- **PostgreSQL 15** (production) or **SQLite** (dev)
- **Wazuh 4.x server** (Manager + Indexer accessible from Django host)
- **Nginx** (production reverse proxy)
- **Git**

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/boniyeamincse/ariba_soc.git
cd ariba_soc
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```ini
DEBUG=True
SECRET_KEY=your-secret-key-here
DB_NAME=ariba_soc
DB_USER=ariba_soc
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432
WAZUH_MANAGER_URL=https://10.24.66.2:55000
WAZUH_MANAGER_USER=soc-api-user
WAZUH_MANAGER_PASSWORD=Care@#$1718
WAZUH_INDEXER_URL=https://10.24.66.2:9200
WAZUH_INDEXER_USER=ariba-soc-reader
WAZUH_INDEXER_PASSWORD=AribaS0C_AlertReader!@#
```

For SQLite dev, set `USE_SQLITE=True` and omit DB_* vars.

### 4. Database Setup

```bash
# Create PostgreSQL database
sudo -u postgres psql -c "CREATE DATABASE ariba_soc;"
sudo -u postgres psql -c "CREATE USER ariba_soc WITH PASSWORD 'your-db-password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ariba_soc TO ariba_soc;"

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 5. Run Development Server

```bash
python manage.py runserver 0.0.0.0:8090
```

Access at `http://localhost:8090`.

## Production Setup

### 1. System Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib
sudo apt install -y libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev
```

### 2. Clone & Configure

```bash
git clone https://github.com/boniyeamincse/ariba_soc.git /opt/ariba_soc
cd /opt/ariba_soc
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment

Set `DEBUG=False` in `.env`. Use a strong `SECRET_KEY`. Configure PostgreSQL.

### 4. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 5. Gunicorn Service

Copy the systemd service:

```bash
sudo cp deploy/ariba-soc.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ariba-soc
sudo systemctl start ariba-soc
```

### 6. Nginx Configuration

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/ariba-soc
sudo ln -s /etc/nginx/sites-available/ariba-soc /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. SSL (Recommended)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 8. Verify

```bash
curl -k https://localhost:8091/api/health/
```

## Docker Setup

```bash
cd deploy
docker-compose up -d
```

This starts both the Django app and PostgreSQL. Configure `.env` for Docker networking.

## Wazuh Connection Verification

After installation, verify integration via the UI:

1. Log in as Admin
2. Navigate to Wazuh Integration
3. Click "Test Manager Connection" and "Test Indexer Connection"
4. Both should return "ok"
5. Click "Force Sync" to import alerts
