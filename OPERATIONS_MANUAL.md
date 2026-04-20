# SGA1 Operations Manual - Guía Diaria & Troubleshooting

---

## 📚 Índice

1. Comandos Diarios Comunes
2. Troubleshooting Común
3. Guía de Backup & Restore
4. Monitoreo & Alertas
5. Actualizaciones & Parches

---

## 🎯 Comandos Diarios Comunes

### Ver estado de servicios
```bash
docker compose ps
# Todos deben estar "Up"
```

### Ver logs en tiempo real
```bash
# Django app
docker compose logs -f web

# Database
docker compose logs -f db

# Redis
docker compose logs -f redis

# Todos
docker compose logs -f
```

### Crear usuario nuevo
```bash
docker compose exec web python manage.py shell
>>> from users.models import Usuario
>>> usuario = Usuario.objects.create(
...     nombre="Nombre Completo",
...     email="email@example.com",
...     cedula="1234567890",
...     rol="ESTUDIANTE"  # o "DOCENTE"
... )
>>> usuario.id
1  # Guardar ID para referencia
>>> exit()
```

### Crear admin (superuser)
```bash
docker compose exec web python manage.py createsuperuser
# Seguir prompts
```

### Importar datos (ETL)
```bash
# Primero: simular (dry-run)
docker compose exec web python manage.py etl_import_json \
  --base-dir base_de_datos_json \
  --ciclo 2025-2026 \
  --dry-run

# Si OK: ejecutar de verdad
docker compose exec web python manage.py etl_import_json \
  --base-dir base_de_datos_json \
  --ciclo 2025-2026

# Con creación de usuarios
docker compose exec web python manage.py etl_import_json \
  --base-dir base_de_datos_json \
  --ciclo 2025-2026 \
  --create-student-users
```

### Hacer backup manual
```bash
# PostgreSQL
docker compose exec -T db pg_dump -U music_user music_registry_db | gzip > backup_$(date +%Y%m%d).sql.gz

# Media files
tar -czf media_backup_$(date +%Y%m%d).tar.gz /path/to/media/
```

### Actualizar aplicación
```bash
git pull origin main
docker compose down
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
```

---

## 🚨 Troubleshooting Común

### Problema: "Service web won't start"

**Síntomas:** 
```
docker compose ps
# web: Exited(1) o similar
```

**Solución:**
```bash
# Ver el error
docker compose logs web | tail -50

# Causas comunes:
# 1. Sintaxis error en settings.py
# 2. Variable de entorno faltante
# 3. Port 8000 ya en uso

# Limpiar y reintentar
docker compose down
docker system prune -f
docker compose up web -d
```

---

### Problema: "Database connection refused"

**Síntomas:**
```
psycopg2.OperationalError: connection to server at "db"...
```

**Solución:**
```bash
# Verificar que DB está healthy
docker compose ps db
# Debe estar "Up (healthy)"

# Si no:
docker compose logs db

# Reiniciar
docker compose restart db

# Esperar ~30 segundos (healthcheck)
sleep 30

# Reintentar
docker compose exec web python manage.py migrate
```

---

### Problema: "Static files not loading" (404 en CSS/JS)

**Síntomas:**
```
Browser: 404 for /static/css/style.css
```

**Solución:**
```bash
# Recolectar static files
docker compose exec web python manage.py collectstatic --clear --noinput

# Verificar que existan
docker compose exec web ls -la /usr/src/app/staticfiles/

# Verificar permisos Nginx
ls -la /home/user/SGA1/staticfiles/

# Si es Nginx:
# Agregar location /static/ {...} en config
sudo systemctl reload nginx
```

---

### Problema: "Email not sending"

**Síntomas:**
```
Email no llega a destinatario
Logs: "SMTPAuthenticationError"
```

**Solución:**
```bash
# 1. Verificar configuración
docker compose exec web python manage.py shell
>>> from django.conf import settings
>>> print(settings.EMAIL_HOST)
>>> print(settings.EMAIL_HOST_USER)
>>> exit()

# 2. Probar envío
docker compose exec web python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail(
...     "Test Subject",
...     "Test Body",
...     "from@example.com",
...     ["to@example.com"],
...     fail_silently=False
... )
>>> exit()

# 3. Si falla:
# - Verificar EMAIL_HOST_PASSWORD es App Password (no contraseña regular)
# - Verificar que .env tiene valores correctos
# - Reiniciar: docker compose restart web
```

---

### Problema: "High memory/CPU usage"

**Síntomas:**
```
docker stats
# Memory o CPU > 80%
```

**Solución:**
```bash
# Identificar culpable
docker stats

# Ver procesos
docker compose exec web ps aux

# Revisar logs para queries lentas
docker compose logs db | grep -i duration | sort | tail -20

# Si DB:
docker compose exec db psql -U music_user -d music_registry_db
# SELECT * FROM pg_stat_activity WHERE state != 'idle';
# \q

# Si web:
docker compose logs web | grep -i error | tail -50

# Posibles soluciones:
# - Escalup recursos (CPU/RAM)
# - Optimizar queries (agregar índices)
# - Configurar caching (Redis)
```

---

### Problema: "SSL certificate expiring soon"

**Síntomas:**
```
Browser warning: "Certificate expires in 30 days"
```

**Solución:**
```bash
# Verificar expiración
sudo openssl x509 -noout -enddate -in /etc/letsencrypt/live/tu-dominio.com/fullchain.pem

# Renovar (manual)
sudo certbot renew

# Auto-renew (debería estar en cron)
(crontab -l 2>/dev/null | grep certbot) || echo "NOT CONFIGURED!"

# Configurar si falta
(crontab -l 2>/dev/null; echo "0 0 1 * * sudo certbot renew --quiet && docker compose restart web") | crontab -

# Verificar después
sudo certbot certificates
```

---

## 💾 Backup & Restore

### Backup Completo
```bash
#!/bin/bash
# backup-full.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/sga1"
mkdir -p $BACKUP_DIR

# DB
docker compose exec -T db pg_dump -U music_user music_registry_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Media
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /home/user/SGA1/media/

# Code (opcional)
tar -czf $BACKUP_DIR/code_$DATE.tar.gz /home/user/SGA1/ --exclude=.git --exclude=.venv

echo "✓ Backup completed: $BACKUP_DIR/db_$DATE.sql.gz"
```

### Restaurar Database
```bash
# 1. Obtener último backup
ls -la /backups/sga1/db_*.sql.gz | tail -1

# 2. Descomprimir y restaurar
gunzip < /backups/sga1/db_20260420.sql.gz | docker compose exec -T db psql -U music_user music_registry_db

# 3. Verificar
docker compose exec db psql -U music_user -d music_registry_db -c "SELECT COUNT(*) FROM users_usuario;"
```

### Restaurar Media
```bash
# 1. Obtener backup
ls -la /backups/sga1/media_*.tar.gz | tail -1

# 2. Restaurar
tar -xzf /backups/sga1/media_20260420.tar.gz -C /

# 3. Verificar permisos
sudo chown -R $USER:$USER /home/user/SGA1/media/
```

---

## 📊 Monitoring & Alertas

### Health Check Endpoint (crear si no existe)
```python
# En urls.py
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok"}, status=200)

path('health/', health_check, name='health_check'),
```

### Monitorear vía cron (cada 5 min)
```bash
# En /usr/local/bin/monitor-sga1.sh
#!/bin/bash
DOMAIN="tu-dominio.com"
LOG="/var/log/sga1-monitor.log"

# Check HTTP response
STATUS=$(curl -s -w "%{http_code}" -o /dev/null https://$DOMAIN/health/)

if [ "$STATUS" != "200" ]; then
    echo "$(date): WARNING - Health check failed: $STATUS" >> $LOG
    # Enviar alerta (email, Slack, etc)
else
    echo "$(date): OK - $STATUS" >> $LOG
fi
```

Agregar cron:
```bash
*/5 * * * * /usr/local/bin/monitor-sga1.sh
```

### Monitoreo con Sentry (opcional)
```bash
# Já está integrado en settings.py si SENTRY_DSN está seteado
# Solo verificar que funciona:
docker compose exec web python manage.py shell
>>> import sentry_sdk
>>> sentry_sdk.capture_message("Test message")
>>> exit()

# Verificar en https://sentry.io/ dashboard
```

---

## 🔄 Actualizaciones & Parches

### Actualizar dependencias (recomendado: mensual)
```bash
# Ver qué puede actualizarse
docker compose exec web pip list --outdated

# Actualizar cautiously:
docker compose exec web pip install --upgrade pip

# Luego reiniciar para verificar compatibility
docker compose restart web
```

### Actualizar código (git)
```bash
# 1. Verificar rama actual
git status  # Debe estar clean

# 2. Pull cambios
git pull origin main

# 3. Revisar cambios
git log -3 --oneline

# 4. Rebuild & restart
docker compose down
docker compose up --build -d

# 5. Ejecutar migraciones si hay
docker compose exec web python manage.py migrate

# 6. Verificar health
curl https://tu-dominio.com/
```

---

## 📞 Contactos & Escalation

Cuando contactar al equipo técnico:
- Error 500: Inmediatamente
- Database offline: Inmediatamente
- SSL certificate expiring: Dentro de 1 semana
- Memory > 90%: Dentro de 1 hora
- Slow queries: Dentro de 1 día

---

## ✅ Daily Checklist (para On-Call)

```bash
# Ejecutar cada mañana
echo "=== Daily Health Check ==="
docker compose ps
echo ""
curl -s https://tu-dominio.com/ > /dev/null && echo "✓ App" || echo "✗ App DOWN"
curl -s https://tu-dominio.com/admin/ > /dev/null && echo "✓ Admin" || echo "✗ Admin DOWN"
curl -s https://tu-dominio.com/graphql/ > /dev/null && echo "✓ GraphQL" || echo "✗ GraphQL DOWN"
echo ""
echo "Disk usage:"
df -h | grep -E "^/dev"
echo ""
echo "Last backup:"
ls -lht /backups/sga1/ | head -1
echo ""
echo "Recent errors:"
docker compose logs web --tail 20 | grep -i error | tail -5
```

---

**Version:** 1.0  
**Last updated:** 2026-04-20  
**Status:** Production Ready

