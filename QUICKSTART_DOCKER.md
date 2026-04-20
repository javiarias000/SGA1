# SGA1 Docker Quickstart

Deploy en 5 minutos.

## Local Development

```bash
# 1. Preparar
cp .env.example .env
nano .env  # Editar SECRET_KEY, DB_PASSWORD

# 2. Build & Start
docker compose build
docker compose up -d

# 3. Migrate
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser

# 4. Check
curl http://localhost          # Frontend
curl http://localhost:8000     # Backend
```

## Production (VPS)

```bash
# 1. Server Setup
ssh user@server
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. Clone & Config
git clone <repo> /opt/sga1
cd /opt/sga1
cp .env.example .env
nano .env  # Cambiar: SECRET_KEY, DB_PASSWORD, ALLOWED_HOSTS, EMAIL_*

# 3. SSL (Let's Encrypt)
sudo certbot certonly --standalone -d tu-dominio.com
sudo cp -r /etc/letsencrypt/live/tu-dominio.com ./ssl
sudo chown -R $USER:$USER ./ssl

# 4. Deploy
docker compose build
docker compose up -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser

# 5. Verify
curl https://tu-dominio.com      # Frontend
curl https://tu-dominio.com/admin/  # Admin
```

## Backups (Cron)

```bash
# /usr/local/bin/backup-sga1.sh
#!/bin/bash
BACKUP_DIR="/backups/sga1"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
docker compose -f /opt/sga1/docker-compose.yml exec -T db pg_dump -U music_user music_registry_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz
find $BACKUP_DIR -type f -mtime +30 -delete

# Cron (2 AM daily)
0 2 * * * /usr/local/bin/backup-sga1.sh
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| frontend | 80/443 | Flutter Web UI |
| backend | 8000 | Django API |
| db | 5432 | PostgreSQL |
| redis | 6379 | Cache/Broker |
| celery_worker | - | Async Tasks |
| celery_beat | - | Scheduled Tasks |

## Useful Commands

```bash
# Logs
docker compose logs -f backend
docker compose logs -f celery_worker

# Stats
docker stats

# Data Import
docker compose exec backend python manage.py etl_import_json --base-dir base_de_datos_json --ciclo 2025-2026

# Restart
docker compose restart backend

# Stop all
docker compose down
```

## Security Checklist

```
[ ] DEBUG=False
[ ] SECRET_KEY unique & strong
[ ] DB_PASSWORD 20+ chars
[ ] ALLOWED_HOSTS correct
[ ] SSL certificate valid
[ ] Email configured
[ ] Backups automated
```

---

Ver `DOCKER_DEPLOYMENT.md` para guía completa.
