# SGA1 — Sistema de Gestión Académica

Sistema integral de gestión académica para el **Conservatorio Bolívar de Ambato**. Monorepo con arquitectura de microservicios que centraliza estudiantes, docentes, calificaciones, asistencia, matrículas y notificaciones por WhatsApp.

---

## Servicios

| Servicio | Tecnología | Puerto | Descripción |
|----------|-----------|--------|-------------|
| `api` | Django 5.2 + DRF + GraphQL | 8000 | API principal: dominio académico + informes WhatsApp |
| `whatsapp` | Node.js + Express | 3001 | Google Sheets, proxy `/api/informes/*` → Django |
| `mobile` | Flutter Web + nginx | 80 | App móvil web |
| `django_web` | nginx → Django | 8001 | Panel web (admin, templates) |
| `db` | PostgreSQL 15 | 5432 | Base de datos principal |
| `redis` | Redis 7 | 6379 | Broker Celery |

---

## Estructura del Repositorio

```
SGA1/
├── services/
│   ├── api/                    ← Django backend (fuente de verdad)
│   │   ├── users/              ← Usuario central, auth, GraphQL
│   │   ├── students/           ← Perfil de estudiante
│   │   ├── teachers/           ← Perfil de docente
│   │   ├── subjects/           ← Materias (instrumento / teoría / agrupación)
│   │   ├── classes/            ← Clases, matrículas, calificaciones, asistencia
│   │   ├── academia/           ← REST API views y serializers
│   │   ├── agente/             ← Agente IA
│   │   ├── informes/           ← Informes WhatsApp (WA send, forms, submissions)
│   │   ├── matriculas/         ← Gestión de matrículas
│   │   ├── home/               ← Landing y vistas base
│   │   └── config/             ← Configuración Django (settings, urls, celery, wsgi)
│   ├── whatsapp/               ← Servicio Node.js
│   │   ├── public/             ← Frontend (index.html, app.js, calificaciones.html)
│   │   ├── server.js           ← Express: Google Sheets + proxy a Django
│   │   └── Dockerfile
│   └── mobile/                 ← App Flutter
├── infra/
│   ├── Dockerfile.api          ← Imagen Django
│   ├── Dockerfile.db           ← Imagen PostgreSQL
│   ├── Dockerfile.frontend     ← Imagen Flutter Web
│   ├── nginx/                  ← nginx.conf, nginx_django.conf
│   └── scripts/                ← init-db.sh, wait-for-db.sh, manage_db.sh
├── data/
│   ├── archivos_formularios/   ← Scripts ETL y archivos raw
│   ├── base_de_datos_json/     ← JSON fuente (matrícula, estudiantes, docentes)
│   └── backups/                ← Backups PostgreSQL
├── tools/                      ← Scripts one-off, migraciones GraphQL
├── docs/                       ← Toda la documentación
├── docker-compose.yml          ← Orquestación de todos los servicios
├── Makefile                    ← Comandos simplificados
└── .env                        ← Variables de entorno
```

---

## Inicio Rápido

### Prerrequisitos

- Docker + Docker Compose
- Git

### 1. Clonar y configurar

```bash
git clone https://github.com/javiarias000/SGA1.git
cd SGA1
cp .env.backend.example .env
# Editar .env con tus credenciales
```

### 2. Levantar todos los servicios

```bash
make up
# o directamente:
docker compose up -d
```

### 3. Verificar

```bash
make ps                    # estado de contenedores
curl http://localhost:8000/api/informes/docentes/   # API Django
# http://localhost:3001    # WhatsApp/Sheets frontend
# http://localhost:8001    # Panel web Django
```

---

## Comandos Makefile

```bash
make up            # Levantar todos los servicios
make down          # Detener
make build         # Reconstruir imágenes
make ps            # Estado de contenedores

make migrate       # Correr migraciones Django
make shell         # Django shell interactivo
make check         # Verificar configuración Django
make test          # Correr suite de tests

make etl-dry       # Preview ETL conservatorio.db → PostgreSQL
make etl           # ETL real

make api-logs      # Logs del servicio API
make wa-logs       # Logs del servicio WhatsApp
```

---

## ETL — Importar datos del conservatorio

El comando `import_from_conservatorio_db` migra docentes, cursos y tutores desde el SQLite histórico (`conservatorio.db`) a PostgreSQL:

```bash
# Preview (sin cambios)
make etl-dry

# Importar
make etl
```

Importa:
- **Docentes** → `Usuario(rol=DOCENTE)` + `Teacher`
- **Cursos** → `GradeLevel`
- **Asignaciones tutor-curso** → `GradeLevel.docente_tutor`

---

## App Django — Módulo `informes`

### Endpoints WhatsApp (`/api/informes/`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `docentes/` | GET | Listado de docentes con aliases frontend |
| `docentes/upsert/` | POST | Crear o actualizar docente |
| `tutores-cursos/` | GET | Asignaciones tutor-curso (incluye `tutoresCursos` camelCase) |
| `grade-levels/` | GET | Listado de cursos |
| `subjects/` | GET | Listado de materias |
| `grades/` | GET | Calificaciones por curso/materia/período |
| `wa/instance/` | POST | Crear instancia Evolution API |
| `wa/status/<name>/` | GET | Estado de instancia WhatsApp |
| `wa/send/` | POST | Enviar mensaje individual |
| `wa/send-grades/` | POST | Envío masivo de informes a representantes |
| `wa/historial/` | GET | Historial de envíos WA |
| `forms/submit/` | POST | Enviar formulario(s) a Google Forms |
| `submissions/` | GET | Historial de submissions |
| `submissions/<pk>/resend/` | POST | Reenviar formulario |
| `submissions/<pk>/mark-wa-sent/` | POST | Marcar como enviado por WA |
| `sesiones/clase/<id>/` | GET | Sesiones de una clase |
| `sesiones/upsert/` | POST | Crear/actualizar sesión |
| `recomendaciones/upsert/` | POST | Crear/actualizar recomendación |

### Arquitectura del módulo `informes`

```
services/api/informes/
├── models.py           ← ConfiguracionWhatsapp, SesionClase, SubmisionFormulario,
│                          RegistroEnvioWhatsapp, RecomendacionEstudiante
├── views.py            ← 18 endpoints REST
├── urls.py             ← Rutas bajo /api/informes/
├── whatsapp.py         ← normalize_phone(), send_text(), build_parent_message()
├── grades.py           ← get_grades(), cálculo parciales/quimestres/anual
├── forms_submitter.py  ← submit_form() a Google Forms
└── management/commands/
    └── import_from_conservatorio_db.py  ← ETL SQLite → PostgreSQL
```

---

## Servicio WhatsApp (Node.js)

El servicio Node.js en `services/whatsapp/` actúa como:

1. **Servidor del frontend** — sirve `public/index.html` con la interfaz de informes
2. **Proxy a Django** — redirige `/api/informes/*` al backend Django (`SGA1_BASE`)
3. **Google Sheets** — operaciones de lectura/escritura de calificaciones
4. **Evolution API** — cliente WhatsApp (instancia directa sin proxy)

### Variables de entorno (`services/whatsapp/.env`)

```env
EVOLUTION_API_URL=https://tu-evolution-api.host
EVOLUTION_API_KEY=tu-api-key
EVOLUTION_INSTANCE=NombreInstancia
OPENAI_API_KEY=sk-...
SGA1_BASE=http://api:8000      # En Docker usa el nombre del servicio
```

---

## Variables de Entorno (`.env` raíz)

```env
# Base de datos
DB_NAME=music_registry_db
DB_USER=music_user
DB_PASSWORD=music_password
DB_HOST=db
DB_PORT=5432

# Django
SECRET_KEY=django-insecure-cambia-esto-en-produccion
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=

# Evolution API (WhatsApp)
EVOLUTION_API_URL=https://tu-evolution-api.host
EVOLUTION_API_KEY=tu-api-key
EVOLUTION_INSTANCE_NAME=NombreInstancia

# OpenAI
OPENAI_API_KEY=sk-...
```

---

## Modelo de Datos Principal

```
Usuario (identidad central)
  ├── Student  →  Enrollment  →  Clase  →  Subject
  │                               └── CalificacionParcial
  │                               └── Asistencia
  └── Teacher
       └── GradeLevel.docente_tutor

informes app:
  ├── ConfiguracionWhatsapp   (instancias Evolution API)
  ├── RegistroEnvioWhatsapp   (historial mensajes WA a representantes)
  ├── SubmisionFormulario     (historial envíos Google Forms)
  ├── SesionClase             (sesiones de clase con Google Sheets)
  └── RecomendacionEstudiante (recomendaciones por sesión)
```

---

## API GraphQL

Endpoint: `http://localhost:8000/graphql/`  
GraphiQL disponible en modo DEBUG.  
Schema: `services/api/config/schema.py`

---

## Desarrollo Local

### Correr manage.py directamente (sin rebuild)

```bash
docker run --rm --network sga1_sga1_network \
  -v $(pwd)/services/api:/usr/src/app \
  -w /usr/src/app \
  -e DB_HOST=sga1_db -e DB_PORT=5432 \
  -e DB_NAME=music_registry_db -e DB_USER=music_user -e DB_PASSWORD=music_password \
  -e SECRET_KEY=django-insecure-dev -e DEBUG=True \
  sga1-backend:latest \
  python manage.py <comando>
```

### App Flutter

```bash
# Desarrollo Flutter (requiere Flutter SDK)
cd services/mobile
flutter run -d chrome
```

---

## Licencia

Uso interno — Conservatorio Bolívar de Ambato.
