# Environment Variables Guide

Guía de variables de entorno por servicio.

## Archivos .env

| Archivo | Servicio | Uso |
|---------|----------|-----|
| `.env.backend` | Django API | Variables críticas (DB, Redis, Email, Security) |
| `.env.frontend` | Flutter Web | Variables frontend (URLs, feature flags) |
| `.env.db` | PostgreSQL | Database config (usuario, password, tuning) |
| `.env.redis` | Redis | Cache & broker config |

---

## 📝 .env.backend (CRÍTICO)

**Variables más importantes:**

```env
# Must change in production
SECRET_KEY=<generate-with-secrets-module>
DB_PASSWORD=<strong-20-chars-min>
EMAIL_HOST_PASSWORD=<app-password-gmail>
REDIS_PASSWORD=<strong>

# Update for your domain
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com
EMAIL_HOST_USER=your-email@gmail.com
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

**Generar SECRET_KEY:**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

**Generar DB_PASSWORD (20+ chars):**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(20))"
```

**Generar REDIS_PASSWORD:**

```bash
python3 -c "import secrets; print(secrets.token_hex(16))"
```

---

## 🎯 .env.db (Database)

**Parámetros de performance tuning:**

```env
# Para servidor con 4GB RAM:
POSTGRES_SHARED_BUFFERS=262144    # 1GB (25% RAM)
POSTGRES_WORK_MEM=20480           # 20MB
POSTGRES_MAINTENANCE_WORK_MEM=524288  # 512MB
POSTGRES_EFFECTIVE_CACHE_SIZE=1048576  # 8GB

# Para servidor con 8GB RAM:
POSTGRES_SHARED_BUFFERS=524288    # 2GB (25% RAM)
POSTGRES_WORK_MEM=40960           # 40MB
POSTGRES_MAINTENANCE_WORK_MEM=1048576  # 1GB
POSTGRES_EFFECTIVE_CACHE_SIZE=2097152  # 16GB

# Para servidor con 16GB RAM:
POSTGRES_SHARED_BUFFERS=1048576   # 4GB (25% RAM)
POSTGRES_WORK_MEM=81920           # 80MB
POSTGRES_MAINTENANCE_WORK_MEM=2097152  # 2GB
POSTGRES_EFFECTIVE_CACHE_SIZE=4194304  # 32GB
```

**Notas:**
- `shared_buffers` = 25% de RAM total
- `work_mem` = RAM / (max_connections * 2)
- `effective_cache_size` = 50-75% de RAM total

---

## 🚀 Usando con Docker Compose

### Opción 1: Un archivo .env principal

```bash
# .env (todas variables combinadas)
cp .env.backend .env
cat .env.db >> .env
cat .env.redis >> .env
```

Docker Compose usa automáticamente `.env` en root.

### Opción 2: Archivos separados (Recomendado para Easypanel)

Actualizar `docker-compose.yml`:

```yaml
services:
  backend:
    env_file:
      - .env.backend
    
  db:
    env_file:
      - .env.db
    
  redis:
    env_file:
      - .env.redis
    
  frontend:
    env_file:
      - .env.frontend
```

### Opción 3: Variables inline (Para CI/CD)

```bash
docker compose run \
  -e SECRET_KEY=xyz \
  -e DB_PASSWORD=abc \
  backend python manage.py migrate
```

---

## 🔒 Valores por Entorno

### Local Development

```env
DEBUG=True
SECRET_KEY=insecure-development-key
ALLOWED_HOSTS=localhost,127.0.0.1
DB_PASSWORD=postgres
REDIS_PASSWORD=
EMAIL_BACKEND=console  # Print to console, don't send
SECURE_SSL_REDIRECT=False
```

### Staging

```env
DEBUG=False
SECRET_KEY=<generated>
ALLOWED_HOSTS=staging.yourdomain.com
DB_PASSWORD=<strong>
SECURE_SSL_REDIRECT=False  # Use only if SSL ready
```

### Production

```env
DEBUG=False
SECRET_KEY=<generated-unique>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_PASSWORD=<strong-30-chars>
REDIS_PASSWORD=<strong>
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

---

## 📋 Checklist Pre-Deploy

- [ ] SECRET_KEY generado y único
- [ ] DB_PASSWORD ≥ 20 caracteres
- [ ] EMAIL configurado (SMTP credentials válidos)
- [ ] ALLOWED_HOSTS actualizado
- [ ] REDIS_PASSWORD configurado
- [ ] DEBUG=False
- [ ] SECURE_SSL_REDIRECT=True (si SSL ready)
- [ ] CORS_ALLOWED_ORIGINS correcto
- [ ] Backups configurados
- [ ] Logs configurados

---

## 🔑 Variables Críticas Explicadas

| Variable | Propósito | Ejemplo |
|----------|-----------|---------|
| `SECRET_KEY` | Seguridad Django (tokens, sessions) | Único, 50+ chars |
| `DB_PASSWORD` | Autenticación PostgreSQL | Strong, 20+ chars |
| `REDIS_PASSWORD` | Autenticación Redis | Strong |
| `EMAIL_HOST_PASSWORD` | App Password Gmail (NO cuenta real) | Gmail App Password |
| `ALLOWED_HOSTS` | Dominios permitidos | yourdomain.com |
| `DEBUG` | Modo debug (NEVER True en prod) | False |
| `SECURE_SSL_REDIRECT` | Forzar HTTPS | True |

---

## 🚨 Seguridad

**NUNCA commitear .env a git:**

```bash
# Verificar .gitignore
cat .gitignore | grep env
# Output: .env, .env.*, .env.local

# Verificar no committed
git log --name-status | grep -i env  # Debe estar vacío
```

**Acceso a valores en producción:**

```bash
# Leer desde servidor (NO copiar local)
ssh user@server 'cat /opt/sga1/.env.backend' | less

# Cambiar valor en producción
ssh user@server 'nano /opt/sga1/.env.backend'
docker compose restart backend  # Aplicar cambios
```

---

## 💡 Pro Tips

### Generar todas passwords de una vez

```bash
cat << 'EOF'
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(20))")
REDIS_PASSWORD=$(python3 -c "import secrets; print(secrets.token_hex(16))")
EOF
```

### Validar variables antes de deploy

```bash
docker compose exec backend python manage.py check --deploy
# Output: System check identified 0 issues (0 silenced)
```

### Verificar que Docker lee variables correctamente

```bash
docker compose exec backend env | grep DJANGO
docker compose exec db env | grep POSTGRES
```

---

## 📚 Referencias

- Django Security: https://docs.djangoproject.com/en/5.2/topics/security/
- PostgreSQL Performance: https://wiki.postgresql.org/wiki/Performance_Optimization
- Redis Configuration: https://redis.io/docs/management/config/
