# Testing Guide - SGA1

Guía completa para testing local de SGA1 (Sistema de Gestión Académica).

## Requisitos Previos

- Python 3.10+
- PostgreSQL 12+ (opcional, se puede usar SQLite para tests rápidos)
- pip (gestor de paquetes de Python)

## Instalación Rápida

### 1. Crear Entorno Virtual

```bash
# Opción A: Usar Makefile
make venv
make install

# Opción B: Manual
python3 -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tus valores (especialmente DB_PASSWORD)
nano .env
```

### Variables Mínimas Requeridas para Testing

```env
# Database
DB_NAME=music_registry_db
DB_USER=music_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Redis (opcional, puede usar valores por defecto)
REDIS_HOST=localhost
REDIS_PORT=6379

# Django
SECRET_KEY=your-secret-key-min-50-chars
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

## Configuración de Base de Datos PostgreSQL

### Opción A: Usar Script Automatizado

```bash
# Crear base de datos
bash manage_db.sh create

# Ejecutar migraciones
bash manage_db.sh migrate

# Ejecutar tests
bash manage_db.sh test

# Todo en uno
bash manage_db.sh full
```

### Opción B: Usar Makefile

```bash
# Crear base de datos
make db-create

# Ejecutar migraciones
make migrate

# Tests
make test

# Todo en uno
make all
```

### Opción C: Manual (PostgreSQL)

```bash
# 1. Crear usuario (como usuario postgres)
sudo -u postgres createuser -P music_user
# Ingresar password cuando se pida

# 2. Crear base de datos
sudo -u postgres createdb -O music_user music_registry_db

# 3. Verificar conexión
psql -U music_user -h localhost -d music_registry_db

# 4. Ejecutar migraciones
python manage.py migrate

# 5. Crear superuser (opcional)
python manage.py createsuperuser
```

## Ejecutar Tests

### Tests Rápidos (Recomendado para Desarrollo)

```bash
# Usa SQLite en memoria (muy rápido)
python -m pytest -v

# O con Makefile
make test-quick
```

### Tests con Cobertura Completa

```bash
# Genera reporte HTML
python -m pytest --cov=. --cov-report=html --cov-report=term-missing

# O con Makefile
make test-coverage
```

Ver resultado en: `htmlcov/index.html`

### Tests Específicos

```bash
# Test un archivo
python -m pytest users/tests.py -v

# Test una clase
python -m pytest users/tests.py::TestUsuarioModel -v

# Test un método
python -m pytest users/tests.py::TestUsuarioModel::test_usuario_create -v

# Tests por marca
python -m pytest -m "unit" -v
python -m pytest -m "integration" -v
```

### Tests de Integración

```bash
# Tests de workflow completo
python -m pytest tests_integration.py -v

# Migraciones
python -m pytest -m "migration" -v
```

## Estructura de Tests

```
proyecto/
├── conftest.py                # Fixtures globales
├── pytest.ini                 # Configuración de pytest
├── users/
│   ├── tests.py              # Tests de modelos Usuario, Profile
│   └── factories.py           # Factory Boy factories
├── subjects/
│   ├── tests.py              # Tests de Subject
│   └── factories.py
├── classes/
│   ├── tests.py              # Tests de Clase, Enrollment
│   ├── tests_models.py        # Tests detallados de modelos
│   └── factories.py
├── students/
│   ├── tests.py              # Tests de Student
│   └── factories.py
├── teachers/
│   ├── tests.py              # Tests de Teacher
│   └── factories.py
├── academia/
│   └── tests.py              # Tests de API REST
└── tests_integration.py        # Tests de workflows
```

## Factory Boy - Crear Datos de Prueba

### Uso Básico

```python
from users.factories import UsuarioFactory, StudentFactory
from subjects.factories import SubjectFactory
from classes.factories import ClaseFactory

# Crear single
usuario = UsuarioFactory()

# Crear múltiples
users = UsuarioFactory.create_batch(5)

# Con atributos específicos
teacher = UsuarioFactory(
    nombre="Prof. García",
    rol="DOCENTE",
    email="garcia@example.com"
)

# SubFactory (relaciones)
student = StudentFactory(
    usuario__nombre="Juan Pérez"  # Crea Usuario con este nombre
)
```

## Fixtures Disponibles (pytest)

```python
import pytest

@pytest.mark.django_db
class TestMyClass:
    def test_something(self, user, student_user, teacher_user, subject, clase, enrollment):
        # Fixtures disponibles:
        # - user: Usuario básico
        # - student_user: Student con Usuario
        # - teacher_user: Teacher con Usuario
        # - subject: Subject
        # - clase: Clase con subject y teacher
        # - enrollment: Enrollment con student y clase
        
        assert user.nombre is not None
```

## Migraciones - Testing

### Ver estado de migraciones

```bash
# Mostrar migraciones pendientes
python manage.py showmigrations

# Mostrar SQL de una migración
python manage.py sqlmigrate students 0001
```

### Testing de Migraciones

```bash
# Ejecutar todas las migraciones
python manage.py migrate

# Revertir última migración
python manage.py migrate students 0001

# Crear nueva migración (después de cambios en models.py)
python manage.py makemigrations

# Tests de migración
python -m pytest -m "migration" -v
```

## ETL Testing

```bash
# Test ETL import (dry-run)
python manage.py etl_import_json \
    --base-dir base_de_datos_json \
    --ciclo 2025-2026 \
    --dry-run

# ETL import actual
python manage.py etl_import_json \
    --base-dir base_de_datos_json \
    --ciclo 2025-2026

# Crear usuarios para estudiantes
python manage.py etl_import_json \
    --base-dir base_de_datos_json \
    --ciclo 2025-2026 \
    --create-student-users
```

## Limpieza y Mantenimiento

```bash
# Limpiar archivos temporales
make clean

# Resetear base de datos
make db-reset

# Verificar integridad del proyecto
python manage.py check

# Ver configuración actual
python manage.py diffsettings
```

## Troubleshooting

### Error: "psycopg2: could not connect to server"

```bash
# Verificar que PostgreSQL está corriendo
sudo systemctl status postgresql

# O iniciar PostgreSQL
sudo systemctl start postgresql
```

### Error: "database does not exist"

```bash
# Crear base de datos
bash manage_db.sh create
# o
make db-create
```

### Error: "permission denied for schema public"

```bash
# Revisar permisos (como usuario postgres)
sudo -u postgres psql
# En psql:
GRANT ALL ON SCHEMA public TO music_user;
```

### Tests lentos

- Usar SQLite para tests rápidos: `TEST_DATABASE=sqlite python -m pytest`
- Usar `pytest -n auto` para tests paralelos (instalar: `pip install pytest-xdist`)

## Integración Continua

Ver `.github/workflows/` para CI/CD configuration (si está disponible).

Para desplegar en EasyPanel:
1. Asegurar que todos los tests pasen: `make test-coverage`
2. Revisar cobertura: > 70% obligatorio
3. Ejecutar `python manage.py check --deploy` para validar producción

## Recursos Adicionales

- Django Testing: https://docs.djangoproject.com/en/5.2/topics/testing/
- Pytest: https://docs.pytest.org/
- Factory Boy: https://factoryboy.readthedocs.io/
- Coverage.py: https://coverage.readthedocs.io/
