# Phase 3: Production Deployment Guide - SGA1

**Objetivo:** Desplegar SGA1 en producción con HTTPS, backups, monitoreo y seguridad completa.

**Tiempo estimado:** 4-6 horas (según infraestructura)

---

## 📋 Pre-Deployment Checklist

### 1. Prepare Repository
- [ ] Rama `main` está limpia (sin cambios pendientes)
- [ ] Último commit: Phase 2 completada
- [ ] `.env.prod` NO está commiteado (verificar con `git check-ignore .env.prod`)
- [ ] `.gitignore` incluye `.env*` ✓

```bash
# Verificar state
git status  # Debe estar clean
git log --oneline -1  # Mostrar último commit
git check-ignore -v .env.prod  # Debe ignorarse
```

### 2. Dominio & DNS
- [ ] Dominio registrado y activo
- [ ] DNS apuntando a servidor IP
- [ ] Verificar: `nslookup tu-dominio.com`

### 3. Servidor (VPS / Hosting)
- [ ] Linux server preparado (Ubuntu 22.04+ recomendado)
- [ ] Docker installed: `docker --version`
- [ ] Docker Compose installed: `docker compose --version`
- [ ] Usuario non-root configurado
- [ ] SSH keys setup

### 4. SSL Certificate
- [ ] Let's Encrypt certificate solicitado
- [ ] Certificate files en `/etc/letsencrypt/live/tu-dominio.com/`

```bash
# Instalar certbot (Ubuntu/Debian)
sudo apt-get install certbot python3-certbot-nginx

# Generar certificate (manual o con DNS)
sudo certbot certonly --manual -d tu-dominio.com -d www.tu-dominio.com
```

### 5. Environment Variables
- [ ] `.env.prod` editado con valores reales
- [ ] SECRET_KEY regenerado para producción
- [ ] DB_PASSWORD fuerte (min 20 chars)
- [ ] EMAIL_HOST_PASSWORD = App Password (no cuenta real)
- [ ] ALLOWED_HOSTS actualizado

---

## 🚀 Deployment Steps

### Paso 1: Clone & Setup en Servidor
```bash
# SSH al servidor
ssh user@tu-dominio.com

# Clone repositorio
git clone https://github.com/tu-usuario/SGA1.git
cd SGA1

# Crear .env desde .env.prod
cp .env.prod .env

# EDITAR .env con valores reales (IMPORTANTE!)
nano .env
# Cambiar: SECRET_KEY, ALLOWED_HOSTS, DB_PASSWORD, EMAIL_*, etc.
```

### Paso 2: Configurar Docker

```bash
# Crear volúmenes persistentes (si necesario)
docker volume create postgres_data
docker volume create static_volume
docker volume create media_volume

# Configurar permisos
sudo chown -R $USER:$USER .

# Crear archivo de logs
mkdir -p logs
touch logs/django.log logs/gunicorn.log
```

### Paso 3: Levantar Servicios
```bash
# Build & start all services
docker compose up --build -d

# Verificar que arranquen
docker compose ps
# Esperado: web, db, redis, beat (si aplica) en "Up"

# Ver logs si hay errores
docker compose logs web
docker compose logs db
```

### Paso 4: Migrar Base de Datos
```bash
# Ejecutar migraciones
docker compose exec web python manage.py migrate

# Crear superuser
docker compose exec web python manage.py createsuperuser

# Verificar que no hay warnings
docker compose exec web python manage.py check --deploy
# Esperado: "System check identified 0 issues"
```

### Paso 5: Configurar HTTPS (Nginx)

Crear `/etc/nginx/sites-available/tu-dominio.com`:

```nginx
# Redirect HTTP -> HTTPS
server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name tu-dominio.com www.tu-dominio.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # HSTS header
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Proxy to Django
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /home/user/SGA1/staticfiles/;
        expires 30d;
    }

    # Media files
    location /media/ {
        alias /home/user/SGA1/media/;
        expires 7d;
    }
}
```

Habilitar sitio:
```bash
sudo ln -s /etc/nginx/sites-available/tu-dominio.com /etc/nginx/sites-enabled/
sudo nginx -t  # Verificar syntax
sudo systemctl restart nginx
```

### Paso 6: Collectstatic & Media

```bash
# Recolectar archivos estáticos
docker compose exec web python manage.py collectstatic --noinput

# Verificar permisos en /media y /staticfiles
docker compose exec web ls -la /usr/src/app/staticfiles/
docker compose exec web ls -la /usr/src/app/media/
```

### Paso 7: Verificar Endpoints
```bash
# Test HTTPS redirect
curl -I https://tu-dominio.com/
# Esperado: 200 OK

# Test admin
curl -I https://tu-dominio.com/admin/
# Esperado: 200 OK

# Test GraphQL
curl -I https://tu-dominio.com/graphql/
# Esperado: 200 OK

# Security headers
curl -I https://tu-dominio.com/ | grep -i "strict-transport"
# Esperado: Strict-Transport-Security header presente
```

---

## 🔒 Post-Deployment Security

### 1. Verificar Security Settings
```bash
docker compose exec web python manage.py check --deploy
# Esperado: "System check identified 0 issues (0 silenced)"
```

### 2. Test SSL Certificate
```bash
# Verificar certificado
sudo openssl x509 -noout -text -in /etc/letsencrypt/live/tu-dominio.com/fullchain.pem

# Online test (en otra máquina)
curl -v https://tu-dominio.com/ 2>&1 | grep -i "certificate"
```

### 3. Verificar Headers de Seguridad
```bash
curl -I https://tu-dominio.com/ | grep -E "Strict-Transport|X-Frame|X-Content"
```

---

## 📊 Database Backups

### Automated Backup (Daily)
Crear script `/usr/local/bin/backup-sga1.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/sga1"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="music_registry_db"
DB_USER="music_user"

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker compose exec -T db pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /home/user/SGA1/media/

# Keep only last 30 days
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $DATE" >> /var/log/sga1-backup.log
```

Hacer ejecutable y agregar a crontab:
```bash
chmod +x /usr/local/bin/backup-sga1.sh

# Cron: diariamente a las 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-sga1.sh") | crontab -
```

---

## 🔍 Monitoring Setup

### 1. Basic Logging
```bash
# Ver logs en tiempo real
docker compose logs -f web

# Guardar logs
docker compose logs web > logs/web.log
docker compose logs db > logs/db.log
```

### 2. Sentry (Error Tracking) - Opcional

```bash
# 1. Crear cuenta en https://sentry.io
# 2. Crear proyecto Django
# 3. Obtener SENTRY_DSN

# 4. Instalar sentry-sdk
pip install sentry-sdk

# 5. Editar .env
echo "SENTRY_DSN=https://xxxxx@sentry.io/xxxxx" >> .env

# 6. Agregar a settings.py (ya está configurado en el repo)
# Reiniciar: docker compose restart web
```

### 3. Health Check
```bash
# Endpoint healthcheck
curl https://tu-dominio.com/
# Si devuelve 200: OK

# Cron job (cada 5 min)
*/5 * * * * curl -f https://tu-dominio.com/ || systemctl restart docker
```

---

## 🎯 Daily Operations

### Crear Usuario Nuevo
```bash
docker compose exec web python manage.py shell
>>> from users.models import Usuario
>>> u = Usuario.objects.create(
...     nombre="Juan Pérez",
...     email="juan@example.com",
...     rol="ESTUDIANTE"
... )
>>> exit()
```

### Importar Datos (ETL)
```bash
docker compose exec web python manage.py etl_import_json \
  --base-dir base_de_datos_json \
  --ciclo 2025-2026 \
  --dry-run  # Primero simular

# Luego ejecutar real
docker compose exec web python manage.py etl_import_json \
  --base-dir base_de_datos_json \
  --ciclo 2025-2026
```

### Ver Estadísticas de Base de Datos
```bash
docker compose exec db psql -U music_user -d music_registry_db -c "
  SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
  FROM pg_tables
  WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

---

## 🚨 Troubleshooting

### Web service no inicia
```bash
docker compose logs web
# Ver error específico

# Reintentar
docker compose down
docker compose up web -d
```

### Database connection error
```bash
# Verificar DB está healthy
docker compose ps db

# Revisar logs DB
docker compose logs db

# Reiniciar DB
docker compose restart db
```

### Static files no cargan
```bash
# Recolectar nuevamente
docker compose exec web python manage.py collectstatic --clear --noinput

# Verificar permisos
docker compose exec web ls -la /usr/src/app/staticfiles/
```

### SSL certificate expired (next year)
```bash
# Renovar antes de expiración
sudo certbot renew

# Auto-renew (cron)
sudo certbot renew --quiet && docker compose restart web
```

---

## 📞 Runbook: Incident Response

### Database Down
1. Verificar: `docker compose ps db`
2. Logs: `docker compose logs db`
3. Restart: `docker compose restart db`
4. Verificar migraciones: `docker compose exec web python manage.py showmigrations`

### High CPU/Memory
1. Verificar: `docker stats`
2. Revisar logs: `docker compose logs web`
3. Analizar queries lentas: `docker compose logs db | grep duration`
4. Escalar recursos si es necesario

### Email no envía
1. Verificar: EMAIL_HOST_USER y EMAIL_HOST_PASSWORD
2. Probar: `docker compose exec web python manage.py shell`
   ```python
   from django.core.mail import send_mail
   send_mail("Test", "Test body", "from@domain", ["to@domain"])
   ```
3. Si falla, revisar logs: `docker compose logs web`

### Backup Failed
1. Verificar espacio: `df -h /backups/`
2. Permisos: `ls -la /backups/`
3. Logs: `tail /var/log/sga1-backup.log`
4. Ejecutar manual si es crítico

---

## ✅ Post-Deployment Verification

Ejecutar después de deploy:

```bash
# Checklist final
[ ] App responde en https://tu-dominio.com/
[ ] Admin accesible en /admin/
[ ] GraphQL funciona en /graphql/
[ ] Security check: 0 warnings
[ ] Tests pasan: docker compose exec web python manage.py test
[ ] Migraciones completas: docker compose exec web python manage.py showmigrations
[ ] Email configurado: prueba manual
[ ] Backups en cron
[ ] SSL valid (no warnings)
[ ] Monitoring activo
[ ] Logs escribiéndose

# Si todo OK:
echo "✅ Production deployment successful"
```

---

## 📚 Additional Resources

- Django Deployment: https://docs.djangoproject.com/en/5.2/howto/deployment/
- Let's Encrypt: https://letsencrypt.org/
- Nginx: https://nginx.org/
- Docker: https://docs.docker.com/

---

**Status:** Ready for Phase 3 Deployment ✅

Próximo: Ejecutar pasos 1-7 en servidor de producción.
