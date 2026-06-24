# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

SGA1 (Sistema de Gestión Académica) — Monorepo for the Conservatorio Bolívar de Ambato. Manages students, teachers, subjects, enrollments, grades, attendance, and WhatsApp notifications. Django project name is `config` (was `music_registry`).

## Repository Layout

```
SGA1/
├── services/
│   ├── api/          ← Django REST + GraphQL backend
│   ├── whatsapp/     ← Node.js / Google Sheets / Evolution API
│   └── mobile/       ← Flutter mobile app
├── infra/
│   ├── Dockerfile.api / Dockerfile.db / Dockerfile.frontend
│   ├── nginx/        ← nginx.conf, nginx_django.conf
│   └── scripts/      ← init-db.sh, wait-for-db.sh, manage_db.sh
├── data/
│   ├── archivos_formularios/   ← ETL scripts and raw data
│   ├── base_de_datos_json/     ← JSON source files
│   └── backups/
├── tools/            ← one-off migration scripts, import scripts
├── docs/             ← all .md documentation
├── docker-compose.yml
├── Makefile
└── .env
```

## Commands

All Django commands run inside Docker against `services/api/`.

```bash
# Start all services
make up           # docker compose up -d
make down         # docker compose down
make build        # rebuild images

# Django management
make migrate      # python manage.py migrate
make shell        # python manage.py shell
make check        # python manage.py check

# ETL — import conservatorio.db data
make etl-dry      # dry-run (preview only)
make etl          # apply to PostgreSQL

# Logs
make api-logs
make wa-logs
```

Manual docker run (when port conflicts exist — see below):
```bash
docker run --rm --network sga1_sga1_network \
  -v /home/javlabs/n8nauto/SGA1/services/api:/usr/src/app \
  -w /usr/src/app \
  -e DB_HOST=sga1_db -e DB_PORT=5432 \
  -e DB_NAME=music_registry_db -e DB_USER=music_user -e DB_PASSWORD=music_password \
  -e 'SECRET_KEY=django-insecure-sga1-key' -e DEBUG=True \
  sga1-backend:latest \
  python manage.py <comando>
```

## Port Conflicts on This Machine

- **Port 8000**: occupied by `Appointment-Booking-Automator` — do NOT kill
- **Port 5432**: occupied by `elated_hamilton` container — do NOT kill
- Use `DB_PORT=5434` in `.env` for host mapping; use `DB_PORT=5432` in `docker run` commands (internal network)
- Development backend runs on port **8002**

## Architecture

### Services

| Service | Tech | Port | Role |
|---------|------|------|------|
| `api` | Django 5.2 + DRF + GraphQL | 8000 | Core domain: students, grades, teachers, WA |
| `whatsapp` | Node.js + Express | 3001 | Google Sheets, proxies `/api/informes/*` → Django |
| `mobile` | Flutter Web | 80 | Mobile app (via nginx) |
| `django_web` | nginx → Django | 8001 | Django templates, admin |
| `db` | PostgreSQL 15 | 5432 | Primary database |
| `redis` | Redis 7 | 6379 | Celery broker |

### Django Apps (`services/api/`)

| App | Role |
|-----|------|
| `users` | Central domain model (`Usuario`), auth backend, GraphQL, login views |
| `students` | `Student` profile extending `Usuario` |
| `teachers` | `Teacher` profile extending `Usuario` |
| `subjects` | `Subject` model (INSTRUMENTO / TEORIA / AGRUPACION) |
| `classes` | `GradeLevel`, `Clase`, `Enrollment`, `CalificacionParcial`, `Asistencia` |
| `academia` | REST API views and serializers |
| `agente` | AI agent functionality |
| `informes` | WhatsApp reports: WA send, forms, submissions, docentes, ETL |
| `matriculas` | Enrollment/registration management |
| `home` | Basic landing views |

### Django Project Config (`services/api/config/`)

Was `music_registry/`. Contains `settings.py`, `urls.py`, `celery.py`, `wsgi.py`, `asgi.py`, `schema.py`.

### Key Design: Unified `users.Usuario`

`Usuario` is the single domain identity. Django's `User` links to it optionally via `Usuario.auth_user` (OneToOne). All person data (nombre, email, cedula, phone) lives in `Usuario`. `Student` and `Teacher` are profiles that extend it with OneToOne.

### WhatsApp Service (`services/whatsapp/`)

Node.js + Express. Proxies `/api/informes/*` → Django API via `SGA1_BASE` env var. Google Sheets operations (auth-status, smart-load, tab-data) stay on Node.js. Evolution API URL: configured via `.env`.

### GraphQL

Endpoint: `/graphql/` (uses `AnonymousGraphQLView` — no auth during migration phase).
Schema: `config/schema.py` composes queries from `users/graphql/`.

### REST API

Token + Session auth via DRF. Endpoints under `/api/` (users), `/academia/`, `/api/informes/`.

### Data Model (key relationships)

```
Usuario (1) ─── (1) Student ── (N) Enrollment ── (1) Clase ── (1) Subject
        (1) ─── (1) Teacher
Enrollment also carries: docente (Usuario FK)
CalificacionParcial links Student + Subject + TipoAporte + quimestre/parcial
```

### ETL Pipeline

Source: Excel/CSV → JSON in `data/base_de_datos_json/` → DB via `etl_import_json`.
WhatsApp ETL: `conservatorio.db` (SQLite from `services/whatsapp/`) → PostgreSQL via `import_from_conservatorio_db`.

### Database

PostgreSQL in Docker (`music_registry_db`). Env vars: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.

### Flutter Mobile App

Located in `services/mobile/`. Communicates with Django backend.
