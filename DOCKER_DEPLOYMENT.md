# SGA1 Docker Deployment Guide

Guía para desplegar SGA1 usando Docker y Docker Compose en cualquier servidor.

## 🏗️ Estructura

```
├── Dockerfile.backend        # Django + Gunicorn
├── Dockerfile.frontend       # Flutter Web + Nginx
├── Dockerfile.database       # PostgreSQL 16
├── docker-compose.yml        # Orquestador
├── nginx.conf               # Configuración Nginx
├── init-db.sh              # Script inicialización DB
├── .env.example            # Variables de ambiente
└── requirements.txt        # Dependencias Python
```

## 📋 Requisitos Previos

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM mínimo
- 20GB almacenamiento libre
- Dominio registrado + DNS configurado (producción)

```bash
# Verificar instalación
docker --version
docker compose version
```

## 🚀 Deployment Local

### 1. Clonar y Preparar

```bash
git clone <tu-repo>
cd SGA1
cp .env.example .env
```

### 2. Configurar Variables de Ambiente

```bash
nano .env  # Editar con valores reales
```

**Variables críticas:**
- `SECRET_KEY`: Generar con `python -c "import secrets; print(secrets.token_urlsafe(50))"`
- `DB_PASSWORD`: Mínimo 20 caracteres
- `ALLOWED_HOSTS`: Tu dominio
- `EMAIL_*`: Configurar SMTP

### 3. Construir e Iniciar

```bash
# Build images
docker compose build

# Iniciar servicios
docker compose up -d

# Verificar estado
docker compose ps

# Ver logs
docker compose logs -f backend
docker compose logs -f frontend
```

### 4. Ejecutar Migraciones

```bash
# En otra terminal
docker compose exec backend python manage.py migrate

# Crear superuser
docker compose exec backend python manage.py createsuperuser

# Recolectar statics
docker compose exec backend python manage.py collectstatic --noinput
```

### 5. Verificar

```bash
# Frontend
curl http://localhost

# Backend API
curl http://localhost:8000/api/

# Admin
curl http://localhost:8000/admin/

# GraphQL
curl http://localhost:8000/graphql/
```

---

## 🌍 Deployment Producción (VPS/Servidor)

### 1. Preparación Servidor

```bash
# SSH al servidor
ssh user@tu-servidor.com

# Actualizar sistema
sudo apt-get update && sudo apt-get upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com | sh

# Añadir usuario a docker group
sudo usermod -aG docker $USER
newgrp docker

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verificar
docker compose version
```

### 2. Clonar Repositorio

```bash
# En /opt o /home/user
cd /opt
sudo git clone <tu-repo> sga1
sudo chown -R $USER:$USER sga1
cd sga1
```

### 3. Configurar SSL (Let's Encrypt)

```bash
# Instalar Certbot
sudo apt-get install certbot python3-certbot-nginx

# Generar certificado
sudo certbot certonly --standalone -d tu-dominio.com -d www.tu-dominio.com

# Copiar a carpeta de proyecto
sudo cp -r /etc/letsencrypt/live/tu-dominio.com ./ssl
sudo chown -R $USER:$USER ./ssl
```

### 4. Actualizar .env

```bash
cp .env.example .env
nano .env

# Cambiar:
# - SECRET_KEY (nuevo)
# - ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
# - DB_PASSWORD (fuerte)
# - EMAIL_* (configurar)
# - SECURE_SSL_REDIRECT=True
# - DEBUG=False
```

### 5. Configurar Nginx Reverso (Opcional)

Si deseas Nginx en host en lugar de Docker:

```bash
# Crear config
sudo nano /etc/nginx/sites-available/tu-dominio.com
```

```nginx
server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tu-dominio.com www.tu-dominio.com;

    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Headers de seguridad
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Proxy a Docker
    location / {
        proxy_pass http://127.0.0.1:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Habilitar:
```bash
sudo ln -s /etc/nginx/sites-available/tu-dominio.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Levantar Servicios

```bash
# Build
docker compose build

# Iniciar
docker compose up -d

# Verificar
docker compose ps
docker compose logs backend
```

### 7. Migraciones y Setup

```bash
# Migrar DB
docker compose exec backend python manage.py migrate

# Crear superuser
docker compose exec backend python manage.py createsuperuser

# Collectstatic
docker compose exec backend python manage.py collectstatic --noinput

# Verificar seguridad
docker compose exec backend python manage.py check --deploy
```

---

## 🔒 Seguridad

### Checklist Post-Deployment

```bash
[ ] DEBUG = False
[ ] SECRET_KEY regenerado
[ ] DB_PASSWORD fuerte (20+ chars)
[ ] ALLOWED_HOSTS correcto
[ ] SECURE_SSL_REDIRECT = True
[ ] SESSION_COOKIE_SECURE = True
[ ] CSRF_COOKIE_SECURE = True
[ ] Email configurado
[ ] SSL certificado válido
[ ] Backup automatizado
[ ] Logs configurados
```

### Verificar Headers de Seguridad

```bash
curl -I https://tu-dominio.com/ | grep -E "Strict-Transport|X-Frame|X-Content"
```

---

## 📊 Backups Automatizados

### Script Diario

```bash
# /usr/local/bin/backup-sga1.sh
#!/bin/bash

BACKUP_DIR="/backups/sga1"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup DB
docker compose exec -T db pg_dump -U music_user music_registry_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup media
tar -czf $BACKUP_DIR/media_$DATE.tar.gz ./media/

# Limpiar backups > 30 días
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $DATE" >> /var/log/sga1-backup.log
```

Hacer ejecutable y agregar cron:

```bash
chmod +x /usr/local/bin/backup-sga1.sh

# Cron: diariamente a las 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * cd /opt/sga1 && /usr/local/bin/backup-sga1.sh") | crontab -
```

---

## 🔧 Operaciones Diarias

### Ver Logs

```bash
# Backend
docker compose logs -f backend

# Celery worker
docker compose logs -f celery_worker

# Base de datos
docker compose logs -f db

# Frontend
docker compose logs -f frontend
```

### Importar Datos (ETL)

```bash
# Simular import
docker compose exec backend python manage.py etl_import_json \
  --base-dir base_de_datos_json \
  --ciclo 2025-2026 \
  --dry-run

# Ejecutar real
docker compose exec backend python manage.py etl_import_json \
  --base-dir base_de_datos_json \
  --ciclo 2025-2026
```

### Crear Usuario Manual

```bash
docker compose exec backend python manage.py shell
>>> from users.models import Usuario
>>> u = Usuario.objects.create(
...     nombre="Juan",
...     email="juan@example.com",
...     rol="ESTUDIANTE"
... )
>>> exit()
```

---

## 🚨 Troubleshooting

### Backend no inicia

```bash
docker compose logs backend

# Reintentar
docker compose restart backend

# Rebuild si es necesario
docker compose down
docker compose build --no-cache backend
docker compose up -d backend
```

### DB connection error

```bash
# Verificar estado
docker compose ps db

# Logs
docker compose logs db

# Reiniciar
docker compose restart db
```

### Static files no cargan

```bash
# Recolectar
docker compose exec backend python manage.py collectstatic --clear --noinput

# Verificar permisos
docker compose exec backend ls -la /usr/src/app/staticfiles/
```

### Memory/CPU alto

```bash
# Ver estadísticas
docker stats

# Limitar recursos (editar docker-compose.yml)
# Añadir bajo service:
# deploy:
#   resources:
#     limits:
#       cpus: '1'
#       memory: 2G
```

---

## 📚 Comandos Útiles

```bash
# Detener servicios
docker compose down

# Remover volúmenes (cuidado: borra datos)
docker compose down -v

# Rebuild específico
docker compose build backend

# Reiniciar un servicio
docker compose restart backend

# Ejecutar comando en contenedor
docker compose exec backend python manage.py check --deploy

# Ver estadísticas de DB
docker compose exec db psql -U music_user -d music_registry_db -c \
  "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) \
   FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema') \
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

---

## ✅ Checklist Pre-Deploy

- [ ] Clonar repo
- [ ] Copiar .env.example → .env
- [ ] Actualizar variables críticas
- [ ] Generar SECRET_KEY
- [ ] Configurar email SMTP
- [ ] SSL generado (producción)
- [ ] Docker/Compose instalado
- [ ] Servidor tiene 4GB+ RAM
- [ ] Espacio disco 20GB+
- [ ] Dominio apuntando a servidor

---

**Status:** Ready for deployment ✅

Próximo: `docker compose up -d`
