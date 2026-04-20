# Deployment Guide - SGA1

Guía para desplegar SGA1 en producción, incluyendo EasyPanel.

## Pre-Deployment Checklist

### 1. Validar Configuración

```bash
# Verificar que todo está OK
python manage.py check --deploy

# Ver diferencias con settings de producción
python manage.py diffsettings --all
```

### 2. Ejecutar Tests Completos

```bash
# Tests con cobertura >= 70%
make test-coverage

# Verificar cobertura
cat htmlcov/index.html | grep "total"

# Security checks
python manage.py check --deploy
```

### 3. Compilar Static Files

```bash
python manage.py collectstatic --noinput --clear
```

## Environment Variables for Production

### Critical Variables (MUST SET)

```env
# SECURITY
SECRET_KEY=generate-secure-key-min-50-chars-use-`python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# DATABASE
DB_ENGINE=django.db.backends.postgresql
DB_NAME=music_registry_prod
DB_USER=music_prod_user
DB_PASSWORD=use-strong-password-min-32-chars
DB_HOST=your-db-host
DB_PORT=5432

# REDIS
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=use-strong-password-optional

# EMAIL
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=SGA <noreply@yourdomain.com>

# SECURITY HEADERS
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_BROWSER_XSS_FILTER=True
X_FRAME_OPTIONS=DENY
```

### Optional Variables

```env
# WHATSAPP
EVOLUTION_API_URL=https://your-evolution-instance.com
EVOLUTION_API_KEY=your-api-key
EVOLUTION_INSTANCE_NAME=conservatorio

# LOGGING
LOG_LEVEL=WARNING
LOG_FORMAT=json

# PERFORMANCE
WORKERS=4
WORKER_CLASS=sync
TIMEOUT=120
```

## EasyPanel Deployment

### 1. Prepare Application

```bash
# 1. Ensure all tests pass
make test-coverage

# 2. Create requirements.txt (already exists)
# pip freeze > requirements.txt  # Already done

# 3. Ensure .env.example is up-to-date
# (Already created with all variables)

# 4. Create manage.py hook file for EasyPanel
```

### 2. EasyPanel Configuration

Create file: `.easypanel/app.yaml`

```yaml
services:
  web:
    image: python:3.12-slim
    buildpack: python
    ports:
      - 8000
    env:
      - DEBUG=False
      - WORKERS=4
      - WORKER_CLASS=sync
    volumes:
      - ./staticfiles:/app/staticfiles
      - ./media:/app/media
    startup: |
      pip install -r requirements.txt
      python manage.py migrate
      python manage.py collectstatic --noinput
      gunicorn --workers 4 --bind 0.0.0.0:8000 music_registry.wsgi
  
  db:
    image: postgres:15
    env:
      - POSTGRES_DB=music_registry_prod
      - POSTGRES_USER=music_prod_user
      - POSTGRES_PASSWORD=your-secure-password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - 6379

volumes:
  postgres_data:
```

### 3. Deploy via EasyPanel

1. **Connect Repository**
   - Go to EasyPanel Dashboard
   - Click "New Application"
   - Select "Python" as runtime
   - Connect your Git repository
   - Select branch: `main`

2. **Configure Environment**
   - Set all environment variables from `.env.example`
   - Use strong passwords for DB_PASSWORD and SECRET_KEY
   - Set DEBUG=False
   - Set ALLOWED_HOSTS to your domain

3. **Configure Build**
   ```
   Build Command: pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
   Start Command: gunicorn --workers 4 --bind 0.0.0.0:8000 music_registry.wsgi
   ```

4. **Database**
   - EasyPanel will provide PostgreSQL
   - Copy connection details to environment variables
   - Run: `python manage.py migrate`

5. **Deploy**
   - Click "Deploy"
   - Monitor deployment logs
   - Access application at provided URL

## Docker Deployment (Alternative)

### Build and Run Locally

```bash
# Build image
docker build -t sga1:latest .

# Run with docker-compose
docker compose up -d

# Create superuser
docker compose exec web python manage.py createsuperuser

# Import data
docker compose exec web python manage.py etl_import_json \
  --base-dir base_de_datos_json \
  --ciclo 2025-2026
```

### Push to Docker Registry

```bash
# Tag image
docker tag sga1:latest yourusername/sga1:latest

# Login
docker login

# Push
docker push yourusername/sga1:latest
```

## Post-Deployment

### 1. Verify Deployment

```bash
# Check application health
curl https://yourdomain.com/
curl https://yourdomain.com/admin/

# Check Django
curl https://yourdomain.com/api/token/auth/

# Check GraphQL
curl https://yourdomain.com/graphql/
```

### 2. Configure SSL/TLS

- EasyPanel should provide automatic SSL (Let's Encrypt)
- Verify HTTPS is enforced in settings
- Check SECURE_SSL_REDIRECT=True

### 3. Setup Monitoring

```bash
# Check logs
# In EasyPanel: Application > Logs

# Monitor performance
# In EasyPanel: Application > Metrics

# Setup alerts
# In EasyPanel: Application > Alerts
```

### 4. Database Backups

```bash
# In EasyPanel:
# Database > Backups
# Set automatic daily backups

# Manual backup
pg_dump -U music_prod_user -h your-db-host music_registry_prod > backup_$(date +%Y%m%d).sql

# Restore backup
psql -U music_prod_user -h your-db-host music_registry_prod < backup_20240415.sql
```

## Troubleshooting

### Static Files Not Loading

```bash
# Collect static files
python manage.py collectstatic --noinput --clear

# Verify permissions
ls -la staticfiles/

# Check settings
python manage.py diffsettings | grep STATIC
```

### Database Connection Error

```bash
# Test connection
python manage.py dbshell

# Check environment variables
echo $DB_HOST
echo $DB_NAME

# Verify credentials
psql -U music_prod_user -h your-db-host -d music_registry_prod -c "SELECT version();"
```

### Migration Issues

```bash
# Show pending migrations
python manage.py showmigrations

# Rollback to specific migration
python manage.py migrate app_name 0001

# Apply all migrations
python manage.py migrate

# Check migration status
python manage.py showmigrations --list
```

### Email Not Working

```bash
# Test email
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'This is a test', 'noreply@yourdomain.com', ['your@email.com'])
```

### High Memory Usage

```bash
# Check worker count
# Reduce WORKERS in environment variables

# Check query performance
python manage.py shell
>>> from django.db import connection
>>> from django.test.utils import override_settings
>>> connection.queries  # See slow queries
```

## Performance Tuning

### Database Optimization

```python
# In settings.py or manage Django commands:
# - Use select_related() for ForeignKey
# - Use prefetch_related() for reverse relations
# - Add database indexes
# - Use pagination
```

### Redis Caching

```python
# Set cache backend in settings.py
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
        }
    }
}
```

### Load Balancing

- EasyPanel handles load balancing automatically
- Configure health check endpoint: `/`
- Set up multiple replicas in EasyPanel dashboard

## Security Checklist

- [ ] DEBUG=False in production
- [ ] SECRET_KEY is strong and unique
- [ ] ALLOWED_HOSTS configured correctly
- [ ] SSL/TLS enabled (HTTPS)
- [ ] Database password is strong
- [ ] CSRF protection enabled
- [ ] Security headers configured
- [ ] Regular backups enabled
- [ ] Monitoring and alerts configured
- [ ] Admin panel restricted by IP if possible

## Rollback Procedure

If something goes wrong:

```bash
# 1. Revert to previous commit
git revert HEAD

# 2. Trigger EasyPanel redeploy
# Option A: Push to repo (EasyPanel auto-deploys)
git push origin main

# Option B: Manual deploy in EasyPanel
# Application > Deploy > Redeploy previous version

# 3. Rollback database if needed
# Database > Backups > Restore
```

## Support & Monitoring

- **EasyPanel Logs**: Application > Logs
- **Error Tracking**: Configure Sentry (optional)
- **Performance Monitoring**: Configure NewRelic (optional)
- **Uptime Monitoring**: Configure Pingdom/UptimeRobot

## Additional Resources

- Django Deployment: https://docs.djangoproject.com/en/5.2/howto/deployment/
- EasyPanel Docs: https://easypanel.io/docs
- Gunicorn: https://gunicorn.org/
- PostgreSQL: https://www.postgresql.org/docs/
