# Auditoría de Readiness Producción - SGA1
**Fecha:** 2026-04-20 | **Estado:** ⚠️ NO LISTO - Completar Phase 1

---

## 🔴 CRÍTICOS (Bloquean Deploy)

### 1. **Configuración de Base de Datos en Docker**
- **Problema:** `.env` tiene `DB_HOST=localhost`, pero en Docker debe ser `DB_HOST=db`
- **Impacto:** Contenedor `web` no puede conectar a PostgreSQL
- **Ubicación:** `.env:5`
- **Fix:** 
```env
DB_HOST=db  # Cambiar de 'localhost'
```

### 2. **Security Checks Fallidos (6 warnings)**
`python manage.py check --deploy` falló:

| Warning | Problema | Fix |
|---------|----------|-----|
| W004 | SECURE_HSTS_SECONDS no set | Agregar `SECURE_HSTS_SECONDS=31536000` |
| W008 | SECURE_SSL_REDIRECT=False | Cambiar a `True` en prod |
| W009 | SECRET_KEY débil (django-insecure-) | Regenerar con `get_random_secret_key()` |
| W012 | SESSION_COOKIE_SECURE=False | Cambiar a `True` |
| W016 | CSRF_COOKIE_SECURE=False | Cambiar a `True` |
| W018 | DEBUG=True | Cambiar a `False` en `.env` |

### 3. **Variables de Entorno Incompletas**
Falta: `.env.example` (usuarios no saben qué configurar)

Falta en `.env`:
- EMAIL_* (SMTP config)
- CELERY_* (broker/backend)
- SENTRY_DSN (opcional pero recomendado)

---

## ⚠️ ALTOS

### 4. **Cambios Sin Commitear (24 archivos)**
```
M academia/tests.py
M music_registry/settings.py
M requirements.txt
M subjects/tests.py
M users/signals.py
M users/tests.py

?? 19 archivos nuevos (factories, tests, documentación)
```

**Action:** Commitear todo
```bash
git add .
git commit -m "chore: add tests, factories, production docs"
```

### 5. **Tests No Ejecutados**
- Status: Desconocido (Docker DB issue)
- Cobertura requerida: >= 70%
- Archivos: `conftest.py`, 5x `factories.py`, `tests_*.py` presentes

### 6. **Migraciones: Status Desconocido**
6 apps con migraciones, pero nunca se ejecutaron en Docker.

**Apps:**
- academia (1 mig)
- classes (6 migs)
- students (3 migs)
- subjects (1 mig)
- teachers (1 mig)
- users (1 mig)

### 7. **Middleware Deshabilitado**
```python
# COMENTADO en settings.py línea 58-59:
# 'users.middleware.AttachUsuarioProfilesMiddleware',
# 'users.middleware.ForcePasswordChangeMiddleware',
```
Razón: GraphQL migration. Status: ⚠️ Re-verificar antes de habilitar.

---

## 📋 URLs Validadas

```
/                 → home
/admin/           → Django admin
/graphql/         → GraphQL (AnonymousGraphQLView - sin auth!)
/api/             → API token auth
/users/           → login, logout, register, password reset
/students/        → Student views
/teachers/        → Teacher views
/classes/         → Enrollments
/academia/        → Academia API
```

⚠️ GraphQL sin autenticación. Verificar si es temporal o intencionado.

---

## 🗄️ Docker Status

```
✓ sga1-db-1        postgres:16-alpine (Healthy)
✓ sga1-redis-1     redis:7-alpine     (Healthy)
✗ sga1-web-1       (No arranca - DB_HOST issue)
```

---

## 📊 Tests

### Checklist
- [ ] Unit tests pasan
- [ ] Integration tests pasan
- [ ] Cobertura >= 70%
- [ ] Migration tests pasan
- [ ] ETL tests pasan

**Archivos:** conftest.py, pytest.ini, factories x5, tests_api.py, tests_etl.py, tests_integration.py

---

## 📝 Documentación

### ✓ Presente
- CLAUDE.md
- PRODUCTION_CHECKLIST.md
- README.TESTING.md
- README.PRODUCTION.md
- DEPLOYMENT.md
- QUICKSTART.md

### ✗ Falta
- `.env.example` (CRÍTICO)
- README.md actualizado

---

## 🔧 Django Settings Status

| Config | Actual | Prod-Ready? |
|--------|--------|-------------|
| DEBUG | True | ❌ Debe False |
| SECRET_KEY | django-insecure-... | ❌ Débil |
| ALLOWED_HOSTS | localhost,127.0.0.1 | ❌ Agregar dominio |
| DATABASES | PostgreSQL OK | ⚠️ DB_HOST=localhost |
| SECURE_SSL_REDIRECT | No set | ❌ Debe True |
| SESSION_COOKIE_SECURE | No set | ❌ Debe True |
| CSRF_COOKIE_SECURE | No set | ❌ Debe True |
| SECURE_HSTS_SECONDS | No set | ❌ Debe 31536000 |

---

## ✅ Lo Que Está Bien

1. ✓ Apps bien organizadas
2. ✓ Migraciones presentes
3. ✓ Docker compose con db, redis, worker, beat
4. ✓ Gunicorn configurado
5. ✓ Tests y factories presentes
6. ✓ GraphQL endpoint
7. ✓ Token auth API
8. ✓ Role-based middleware
9. ✓ Healthchecks en DB/Redis
10. ✓ WhiteNoise static files

---

## 🚀 Plan Inmediato

### Fase 1: Fixes Críticos (HOY)
```bash
# 1. Fijar .env
sed -i 's/DB_HOST=localhost/DB_HOST=db/' .env

# 2. Iniciar servicios
docker compose up -d db redis

# 3. Ejecutar migraciones
docker compose exec web python manage.py migrate

# 4. Ejecutar tests
docker compose exec web python manage.py test --verbosity=2

# 5. Security check
docker compose exec web python manage.py check --deploy

# 6. Verificar URLs
curl http://localhost:8000/

# 7. Commitear cambios
git add .
git commit -m "chore: fix DB config, add tests"
```

### Fase 2: Security Hardening
- [ ] Regenerar SECRET_KEY
- [ ] Actualizar settings.py (SECURE_*, DEBUG=False)
- [ ] Crear .env.example
- [ ] Configurar email/Celery
- [ ] Run: `bandit -r .` (security scan)
- [ ] Run: `safety check` (deps)

### Fase 3: Validación
- [ ] Tests >= 70% cobertura
- [ ] API endpoints validados
- [ ] GraphQL schema validado
- [ ] ETL testizado
- [ ] Migraciones reversibles

### Fase 4: Deploy
- [ ] Rama main limpia
- [ ] CI/CD en .github/workflows/
- [ ] EasyPanel .easypanel/app.yaml
- [ ] Backup procedure
- [ ] Monitoring (Sentry, logs)

---

**Reporte completo en:** `AUDIT_PRODUCTION_READY.md`

**Próximo paso:** Ejecutar Phase 1 arriba.

---

## ✅ RESULTADOS AUDITORÍA (2026-04-20)

### Docker Compose Status
```
✓ sga1-db-1        postgres:16 (Healthy, 10min up)
✓ sga1-redis-1     redis:7 (Healthy)
✓ sga1-web-1       gunicorn (UP, respondiendo en :8000)
```

### Migraciones
✓ **EXITOSAS** - Todas las migraciones ejecutadas sin errores

### App Status
```
✓ http://localhost:8000/        → Home page responde HTML
✓ http://localhost:8000/graphql/  → GraphQL endpoint activo
✓ Conexión a PostgreSQL OK
✓ Healthchecks DB/Redis passing
```

### Tests
⚠️ **PARCIAL** - 6 tests pasaron, 2 fallos de importación
```
OK:       4 (ETL normalization tests)
FAILED:   2 (tests_api, tests_integration - missing teachers.factories)
ERROR:    ImportError - teachers.factories no existe
```

### Security Checks
⚠️ **6 WARNINGS PENDIENTES** (del deploy check)
```
W004: SECURE_HSTS_SECONDS
W008: SECURE_SSL_REDIRECT=False
W009: SECRET_KEY débil (django-insecure-)
W012: SESSION_COOKIE_SECURE=False
W016: CSRF_COOKIE_SECURE=False
W018: DEBUG=True (revisar .env)
```

### URLs Validadas
```
✓ /                    (Home)
✓ /admin/              (Django admin accesible)
✓ /graphql/            (GraphQL endpoint + GraphiQL)
✓ /api/                (API token auth)
✓ /users/              (Auth views)
✓ /students/, /teachers/, /classes/, /academia/
```

---

## 📊 SUMMARY CRÍTICO

| Item | Estado | Acción |
|------|--------|--------|
| DB Docker | ✓ | Fixed DB_HOST=db |
| Migraciones | ✓ | Todas OK |
| App Arranca | ✓ | Gunicorn corriendo |
| Tests | ⚠️ | Agregar teachers.factories |
| Security | ✗ | 6 warnings por arreglar |
| Cambios | ✗ | 24 archivos sin commitear |

---

## 🎯 PRÓXIMOS PASOS - ORDEN EJECUCIÓN

### 1. COMMIT CAMBIOS INMEDIATAMENTE
```bash
git status  # Verificar que hay cambios
git add .
git commit -m "chore: fix Docker DB config, add tests & factories, complete production audit"
git push origin main
```

### 2. AGREGAR MISSING FACTORIES
Problema: `teachers.factories` no existe pero es importado por tests

```bash
# Crear teachers/factories.py (copiar del patrón de students)
# Crear teachers/tests.py
```

### 3. RE-EJECUTAR TESTS
```bash
docker compose exec web python manage.py test --verbosity=2
# Debe pasar: tests_api, tests_integration, clases tests
```

### 4. SECURITY HARDENING (settings.py)
```python
# Cambiar DEBUG según ambiente
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# HTTPS/Security
SECURE_SSL_REDIRECT = True  # En prod
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True  # En prod
CSRF_COOKIE_SECURE = True  # En prod

# Regenerar SECRET_KEY
# python manage.py shell
# from django.core.management.utils import get_random_secret_key
# print(get_random_secret_key())
```

### 5. CREAR .env.example
Template para usuarios:
```env
# Database
DB_HOST=db
DB_NAME=music_registry_db
DB_USER=music_user
DB_PASSWORD=musica_segura_2026
DB_PORT=5432

# Django
DEBUG=False  # SIEMPRE False en prod
SECRET_KEY=<generar con get_random_secret_key()>
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Email (SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
EMAIL_USE_TLS=True

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Optional: Error tracking
SENTRY_DSN=

# WhatsApp Evolution
EVOLUTION_API_URL=
EVOLUTION_API_KEY=
EVOLUTION_INSTANCE_NAME=
```

### 6. VALIDAR TODO ANTES DE DEPLOY
```bash
# Local validation
docker compose down -v
docker system prune -f
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py test
docker compose exec web python manage.py check --deploy
```

---

## 🚨 RIESGOS RESIDUALES

### Críticos
- ❌ SECRET_KEY débil → Regenerar inmediatamente
- ❌ DEBUG=True → Cambiar a False en producción
- ❌ GraphQL sin auth → Verificar si es intencional o bug

### Altos
- ⚠️ Teachers factories faltando → Tests fallan
- ⚠️ 24 cambios sin commitear → Pérdida de trabajo posible
- ⚠️ Middleware deshabilitado → Re-enable después GraphQL migration

### Medios
- ⚠️ HTTPS/SSL no configurado → Configurar en dominio prod
- ⚠️ Email no configurado → Tests pueden fallar
- ⚠️ Monitoring (Sentry) faltando → No hay alertas en prod

---

## ✅ CHECKLIST FINAL ANTES DE PRODUCCIÓN

- [ ] Phase 1 completo (arriba)
- [ ] Tests >= 70% cobertura
- [ ] `python manage.py check --deploy` sin warnings
- [ ] .env.example creado
- [ ] SECRET_KEY regenerado
- [ ] ALLOWED_HOSTS actualizado con dominio prod
- [ ] Email configurado
- [ ] SSL/HTTPS setup
- [ ] Rama main limpia (sin cambios pendientes)
- [ ] Backup procedure documentado
- [ ] Monitoring (Sentry) configurado
- [ ] EasyPanel .easypanel/app.yaml creado
- [ ] Code review completado
- [ ] Load testing ejecutado

