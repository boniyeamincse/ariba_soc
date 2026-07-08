# Installation Guide

## 1. System Requirements
- **OS:** Linux (Ubuntu 20.04/22.04 recommended)
- **Python:** 3.10+
- **Database:** PostgreSQL (Production) / SQLite (Development)

## 2. Dependencies
Ensure you have `pip` and `virtualenv` installed.
```bash
sudo apt update
sudo apt install python3-venv python3-pip libpq-dev
```

## 3. Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. Environment Variables
Copy `.env.example` to `.env` and fill in the necessary details (Database credentials, Wazuh API keys, Django Secret Key).
```bash
cp .env.example .env
```

## 5. Migrations & Superuser
```bash
python manage.py migrate
python manage.py createsuperuser
```

## 6. Run Server
```bash
python manage.py runserver 0.0.0.0:8090
```
