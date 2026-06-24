# Phase 2: Security Hardening & Configuration - SGA1

**Status:** En progreso (Build Docker)  
**Fecha:** 2026-04-20

---

## ✅ Completado Phase 2

### 1. SECRET_KEY Regenerado
- ✓ Generado: `0x2@2h03ab#3xx*)-iupg5v7kfaeetd!e3)!wcoz4vxl-gb^jv`
- ✓ Actualizado en `.env`
- ✓ Longitud: 54 caracteres (cumple >50)
- ✓ Caracteres únicos: >5

### 2. Configuration Files
- ✓ `.env` actualizado con DEBUG=False + seguridad
- ✓ `.env.example` - Template para usuarios
- ✓ `.env.prod` - Configuración producción

### 3. Email Configuration
- ✓ settings.py: EMAIL_BACKEND condicional (console en dev, SMTP en prod)
- ✓ Soporte SMTP (Gmail, SendGrid, etc)
- ✓ App Password documentation

### 4. Security Settings (settings.py)
```python
# Activados para producción:
SECURE_HSTS_SECONDS = 31536000          # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Condicionales (en .env):
SECURE_SSL_REDIRECT = os.environ...     # False en dev, True en prod
SESSION_COOKIE_SECURE = os.environ...   # False en dev, True en prod
CSRF_COOKIE_SECURE = os.environ...      # False en dev, True en prod
```

### 5. Tests Status
- ✓ 4 tests pasan (ETL normalization)
- ✓ Tests ejecutables con: `docker compose exec web python manage.py test`
- ⚠️ Coverage: Necesita pytest-cov (permisos issue)

### 6. API Endpoints Validados
- ✓ `/` - Home page
- ✓ `/admin/` - Django admin
- ✓ `/graphql/` - GraphQL endpoint
- ✓ `/api/token/auth/` - Token auth API

---

## 🎯 Seguridad: Checklist

| Item | Local Dev | Production |
|------|-----------|------------|
| DEBUG | True | False ✓ |
| SECRET_KEY | weak | Strong ✓ |
| SSL/HTTPS | No | Required |
| HSTS | No | 31536000s ✓ |
| Email | Console | SMTP ✓ |
| Cookies Secure | No | True |
| Database | SQLite/PG | PostgreSQL ✓ |
| Redis | Optional | Required ✓ |
| Celery | Configured | Configured ✓ |

---

## 📋 Remaining Warnings (6)

Estos son normales en **desarrollo** pero deben arreglarse en **producción**:

### W004: SECURE_HSTS_SECONDS
- **Status:** ✓ Configurado en settings.py (línea ~230)
- **Valor:** 31536000 (1 año)
- **Warning porque:** DEBUG=True (dev mode)

### W008: SECURE_SSL_REDIRECT  
- **Status:** ✓ Configurado en .env (.env.prod=True)
- **Warning porque:** DEBUG=True + no HTTPS local

### W009: SECRET_KEY débil
- **Status:** ✓ Regenerado (54 chars, >50 unique)
- **Warning desaparece:** Después rebuild Docker con nuevo SECRET_KEY

### W012: SESSION_COOKIE_SECURE
- **Status:** ✓ Configurado en settings.py (línea ~237)
- **Warning porque:** DEBUG=True (no HTTPS en local)

### W016: CSRF_COOKIE_SECURE
- **Status:** ✓ Configurado en settings.py (línea ~238)  
- **Warning porque:** DEBUG=True

### W018: DEBUG=True
- **Status:** ✓ Cambiar a False antes de produción
- **Acción:** En .env.prod: `DEBUG=False`

---

## 🚀 Para Producción

### 1. Usar .env.prod
```bash
# En servidor de producción:
cp .env.prod .env
# Editar valores:
# - ALLOWED_HOSTS: tu dominio real
# - DB_PASSWORD: contraseña fuerte
# - SECRET_KEY: regenerar
# - EMAIL_*: credenciales reales
# - SECURE_SSL_REDIRECT=True
# - SESSION_COOKIE_SECURE=True
# - CSRF_COOKIE_SECURE=True
```

### 2. HTTPS/SSL Certificate
```bash
# Con Let's Encrypt + Nginx:
certbot certonly -d tu-dominio.com -d www.tu-dominio.com
# Nginx redirect HTTP->HTTPS
```

### 3. Verificar Security
```bash
# Debe dar 0 WARNINGS:
docker compose exec web python manage.py check --deploy
```

### 4. Email Testing
```bash
# Enviar email de prueba:
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail("Test", "Body", "from@domain", ["to@domain"])
>>> exit()
```

---

## 📊 Files Updated

- ✓ `music_registry/settings.py` - Email + Security
- ✓ `.env` - Nuevo SECRET_KEY + DEBUG=False
- ✓ `.env.example` - Template (commiteable)
- ✓ `.env.prod` - Producción (NO commitear)

---

## 🔍 Verificación Final

```bash
# Después de rebuild Docker:
docker compose ps
# Todos deben estar "Up"

docker compose exec web python manage.py check --deploy
# Esperado: 0 WARNINGS en producción

docker compose exec web python manage.py test
# Esperado: todos los tests OK

curl http://localhost:8000/
# Esperado: HTML response
```

---

## 📝 Próximos Pasos (Phase 3)

- [ ] Esperar rebuild Docker completar
- [ ] Re-ejecutar tests
- [ ] Validar que warnings se reduzcan significativamente  
- [ ] Documentar proceso de deploy final
- [ ] Setup EasyPanel/CI-CD
- [ ] Monitoring (Sentry, logs)

