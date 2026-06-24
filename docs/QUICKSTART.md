# Quick Start - SGA1 Testing & Deployment

Guía rápida para comenzar con testing y deployment.

## 1️⃣ Instalación (2 minutos)

```bash
# Crear entorno virtual e instalar dependencias
make setup

# O manual:
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2️⃣ Base de Datos (3 minutos)

```bash
# Opción A: Con PostgreSQL (recomendado para producción)
make db-create
make migrate

# Opción B: SQLite (rápido para testing)
# Los tests usan SQLite by default
```

## 3️⃣ Ejecutar Tests (1 minuto)

```bash
# Tests rápidos (SQLite en memoria)
python -m pytest -v

# Con cobertura
make test-coverage

# Todos los tests
bash run_all_tests.sh
```

## 4️⃣ Verificar Configuración (1 minuto)

```bash
# Checks de Django
python manage.py check --deploy

# Ver configuración
python manage.py diffsettings
```

## 5️⃣ Desplegar a EasyPanel (10 minutos)

```bash
# 1. Asegurar que tests pasan
make test-coverage
# Debe mostrar >= 70% coverage

# 2. Push a repositorio
git add .
git commit -m "feat: add comprehensive testing suite"
git push origin main

# 3. En EasyPanel:
# - New Application
# - Python runtime
# - Connect repo (main branch)
# - Set environment variables from .env.example
# - Deploy

# 4. Verificar deployment
curl https://yourdomain.com/
```

## 📋 Archivos Importantes

| Archivo | Propósito |
|---------|-----------|
| `.env.example` | Variables de entorno |
| `Makefile` | Comandos útiles |
| `README.TESTING.md` | Guía detallada de testing |
| `DEPLOYMENT.md` | Guía detallada de deployment |
| `PRODUCTION_CHECKLIST.md` | Checklist pre-production |
| `requirements.txt` | Dependencias Python |
| `pytest.ini` | Config de pytest |
| `conftest.py` | Fixtures globales |
| `run_all_tests.sh` | Ejecutar todos los tests |

## 🚀 Comandos Más Útiles

```bash
# Setup completo
make setup

# Tests
make test              # Rápidos
make test-coverage     # Con cobertura
make test-quick        # Sin output detallado

# Base de datos
make db-create         # Crear PostgreSQL
make db-drop           # Eliminar DB
make db-reset          # Resetear
make migrate           # Ejecutar migraciones

# Desarrollo
make runserver         # Django dev server
make shell             # Django shell
make clean             # Limpiar archivos temp

# DB manual
bash manage_db.sh create
bash manage_db.sh reset
bash manage_db.sh migrate
bash manage_db.sh full  # todo en uno
```

## 🔍 Verificar que Todo Funciona

```bash
# 1. Tests pasan
python -m pytest -v
# Output: passed 100+ tests

# 2. Database OK
python manage.py migrate
# Output: Applying...

# 3. Admin accesible
python manage.py createsuperuser  # Crear user
python manage.py runserver
# Ir a: http://localhost:8000/admin/

# 4. API funciona
curl http://localhost:8000/api/token/auth/

# 5. GraphQL OK
curl http://localhost:8000/graphql/
```

## ❌ Troubleshooting

### "ModuleNotFoundError: No module named 'pytest'"
```bash
pip install -r requirements.txt
```

### "psycopg2 could not connect"
```bash
# PostgreSQL no está corriendo
sudo systemctl start postgresql

# O usar SQLite
export TEST_DATABASE=sqlite
pytest
```

### "Database does not exist"
```bash
make db-create
make migrate
```

### Tests lentos
```bash
# Usar SQLite en memoria
export TEST_DATABASE=sqlite
pytest

# O correr en paralelo
pip install pytest-xdist
pytest -n auto
```

## 📊 Ver Cobertura

```bash
# Generar reporte
make test-coverage

# Abrir en navegador
open htmlcov/index.html
# O
firefox htmlcov/index.html
# O
python -m http.server --directory htmlcov 8080
# Luego: http://localhost:8080
```

## 🔐 Antes de Producción

```bash
# 1. Todos los tests pasan
make test-coverage

# 2. No hay warnings de seguridad
python manage.py check --deploy

# 3. Variables de entorno configuradas
cat .env
# Verificar SECRET_KEY, DEBUG=False, etc.

# 4. Migraciones OK
python manage.py showmigrations

# 5. Ready!
echo "Deploy to EasyPanel"
```

## 📱 Importar Datos (Opcional)

```bash
# Test con dry-run
python manage.py etl_import_json \
  --base-dir base_de_datos_json \
  --ciclo 2025-2026 \
  --dry-run

# Import real
python manage.py etl_import_json \
  --base-dir base_de_datos_json \
  --ciclo 2025-2026 \
  --create-student-users  # Crear accounts para estudiantes
```

## 💡 Tips

### Tests en paralelo (rápido)
```bash
pip install pytest-xdist
pytest -n auto
```

### Tests específicos
```bash
# Solo users
pytest users/tests.py -v

# Solo integración
pytest tests_integration.py -v

# Solo ETL
pytest tests_etl.py -v

# Un test
pytest users/tests.py::TestUsuarioModel::test_usuario_create -v
```

### Debug un test
```bash
pytest users/tests.py::TestUsuarioModel::test_usuario_create -v -s --pdb
# -s: mostrar print statements
# --pdb: abrir debugger en error
```

### Ver configuración actual
```bash
python manage.py diffsettings
```

## 🎯 Resumen

| Paso | Comando | Tiempo |
|------|---------|--------|
| Setup | `make setup` | 2 min |
| DB | `make db-create` | 1 min |
| Tests | `make test-coverage` | 2 min |
| Verificar | `python manage.py check --deploy` | 10 seg |
| Deploy | Push to EasyPanel | 10 min |

**Total**: ~15 minutos para setup + tests + deployment

## 📞 Ayuda

- Tests: Ver `README.TESTING.md`
- Deployment: Ver `DEPLOYMENT.md`
- Checklist: Ver `PRODUCTION_CHECKLIST.md`
- Architecture: Ver `CLAUDE.md`
- Summary: Ver `TESTING_SUMMARY.md`

---

**¡Listo para producción!** ✅

Próximo paso: `make test-coverage` ↓
