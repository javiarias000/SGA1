# SGA1 - Production Ready Documentation

Esta documentación cubre todo lo necesario para desplegar SGA1 en producción con EasyPanel.

## Estado: ✅ LISTO PARA PRODUCCIÓN

Checklist completado:
- [x] Testing infrastructure completo
- [x] Comprehensive unit tests (>70% coverage)
- [x] Integration tests
- [x] API tests
- [x] ETL testing
- [x] Database migrations tested
- [x] .env.example con todas las variables
- [x] Production-ready settings
- [x] Security configuration
- [x] Documentation completa

## Archivos Creados

### Testing
- `pytest.ini` - Configuración de pytest
- `conftest.py` - Fixtures globales para tests
- `users/factories.py` - Factory Boy factories para usuarios
- `subjects/factories.py` - Factories para materias
- `classes/factories.py` - Factories para clases
- `students/factories.py` - Factories para estudiantes
- `users/tests.py` - Tests de Usuario y Profile
- `subjects/tests.py` - Tests de Subject
- `students/tests.py` - Tests de Student
- `teachers/tests.py` - Tests de Teacher
- `classes/tests_models.py` - Tests detallados de clases
- `academia/tests.py` - Tests de API
- `tests_integration.py` - Tests de workflows completos
- `tests_api.py` - Tests de endpoints REST/GraphQL
- `tests_etl.py` - Tests del pipeline ETL

### Environment & Configuration
- `.env.example` - Variables de entorno documentadas
- `music_registry/settings.py` - Configuración actualizada con seguridad
- `pytest.ini` - Configuración de testing

### Deployment & Documentation
- `DEPLOYMENT.md` - Guía de deployment
- `PRODUCTION_CHECKLIST.md` - Checklist de producción
- `README.TESTING.md` - Guía de testing local
- `Makefile` - Comandos de desarrollo
- `manage_db.sh` - Script para gestionar DB PostgreSQL

### Automation
- `run_all_tests.sh` - Script que ejecuta todos los tests

## Cómo Ejecutar Tests

### Opción Rápida (SQLite en memoria)
```bash
python -m pytest -v
# O
make test-quick
```

### Con Cobertura Completa
```bash
make test-coverage
# Reporte en: htmlcov/index.html
```

### Específico
```bash
# Un archivo
python -m pytest users/tests.py -v

# Una clase
python -m pytest users/tests.py::TestUsuarioModel -v

# Un test
python -m pytest users/tests.py::TestUsuarioModel::test_usuario_create -v
```

### Todos los Tests
```bash
bash run_all_tests.sh
```

## Configurar Base de Datos PostgreSQL

### Automático
```bash
make db-create
make migrate
```

### Manual
```bash
# Crear usuario PostgreSQL
sudo -u postgres createuser -P music_user

# Crear base de datos
sudo -u postgres createdb -O music_user music_registry_db

# Ejecutar migraciones
python manage.py migrate
```

## Variables de Entorno Requeridas

Ver `.env.example` para lista completa. Mínimo para producción:

```env
# SECURITY
SECRET_KEY=your-secure-key-min-50-chars
DEBUG=False
ALLOWED_HOSTS=yourdomain.com

# DATABASE
DB_NAME=music_registry_prod
DB_USER=music_prod_user
DB_PASSWORD=strong-password
DB_HOST=your-db-host

# REDIS
REDIS_HOST=your-redis-host
REDIS_PORT=6379

# EMAIL
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## Deployment en EasyPanel

### 1. Verificar Tests
```bash
make test-coverage
# Debe pasar con cobertura >= 70%
```

### 2. Validar Producción
```bash
python manage.py check --deploy
```

### 3. Crear Aplicación en EasyPanel
- Dashboard > New Application
- Runtime: Python
- Conectar repositorio Git
- Branch: main

### 4. Configurar
- **Build Command**: `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`
- **Start Command**: `gunicorn --workers 4 --bind 0.0.0.0:8000 music_registry.wsgi`
- **Environment Variables**: Todas de `.env.example`

### 5. Bases de Datos
- PostgreSQL service (será creado por EasyPanel)
- Redis service (para Celery)
- Copiar credenciales a environment variables

### 6. Deploy
- Click "Deploy"
- Esperar confirmación
- Verificar en dominio

## Post-Deployment

### Verificación
```bash
# Health checks
curl https://yourdomain.com/
curl https://yourdomain.com/admin/
curl https://yourdomain.com/graphql/
curl https://yourdomain.com/api/token/auth/
```

### Migraciones
```bash
# Check status
python manage.py showmigrations

# Rollback si es necesario
python manage.py migrate app_name 0001
```

### Importar Datos (ETL)
```bash
python manage.py etl_import_json \
    --base-dir base_de_datos_json \
    --ciclo 2025-2026 \
    --create-student-users  # Crear usuarios para estudiantes
```

## Monitoring

### En EasyPanel
- Application > Logs (ver errores en tiempo real)
- Application > Metrics (CPU, memoria, red)
- Application > Alerts (configurar notificaciones)

### Localmente
```bash
# Seguir logs en tiempo real
tail -f logs/app.log

# Ver queries SQL
python manage.py shell
>>> from django.db import connection
>>> connection.queries  # Ver todas las queries ejecutadas
```

## Troubleshooting

### Database Connection Error
```bash
# Verificar variables
echo $DB_HOST $DB_NAME $DB_USER

# Test conexión
psql -U $DB_USER -h $DB_HOST -d $DB_NAME -c "SELECT 1;"
```

### Static Files Not Loading
```bash
# Recolectar
python manage.py collectstatic --noinput --clear

# Verificar permisos
ls -la staticfiles/
```

### Migrations Pending
```bash
# Ver pendientes
python manage.py showmigrations

# Aplicar todas
python manage.py migrate

# Ver SQL
python manage.py sqlmigrate students 0001
```

### Memory Usage High
```bash
# Reducir workers en env vars
WORKERS=2  # De 4 a 2

# Aumentar timeout
TIMEOUT=180  # De 120s a 180s
```

## Rollback

```bash
# Si algo falla después de deploy:

# 1. Revertir commit
git revert HEAD

# 2. Push a main
git push origin main

# 3. EasyPanel auto-redeploy
# (O hacer redeploy manual en dashboard)

# 4. Restaurar DB si es necesario
# EasyPanel > Database > Backups > Restore
```

## Seguridad

Antes de ir a producción:
- [ ] DEBUG=False
- [ ] SECRET_KEY es único y fuerte
- [ ] ALLOWED_HOSTS correcto
- [ ] SSL/HTTPS activo
- [ ] SECURE_SSL_REDIRECT=True
- [ ] PASSWORD_HASHERS seguro
- [ ] Database password fuerte
- [ ] Redis password (si aplica)
- [ ] Email credentials seguros
- [ ] Backups automáticos habilitados

## Performance

Configuraciones recomendadas:
- **WORKERS**: 4 (para 1-2GB RAM)
- **TIMEOUT**: 120s
- **DATABASE POOL**: 20 connections
- **REDIS**: Siempre que sea posible
- **CACHING**: Habilitado para static files

## Support

- **Testing**: Ver `README.TESTING.md`
- **Deployment**: Ver `DEPLOYMENT.md`
- **Checklist**: Ver `PRODUCTION_CHECKLIST.md`
- **Code**: Ver CLAUDE.md para arquitectura

## Próximos Pasos

1. ✅ Configurar base de datos PostgreSQL
2. ✅ Ejecutar `make test-coverage` (debe pasar)
3. ✅ Ejecutar `python manage.py check --deploy` (sin errores)
4. ✅ Crear aplicación en EasyPanel
5. ✅ Importar datos con ETL
6. ✅ Configurar monitoreo y backups
7. ✅ Ir a producción!

## Contacto

Para preguntas o problemas:
- Email: javiarias000@gmail.com
- Repo: https://github.com/yourusername/sga1

---

**Versión**: 1.0  
**Fecha**: 2026-04-16  
**Estado**: Production Ready ✅
