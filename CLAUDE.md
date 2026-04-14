# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SGA1 (Sistema de Gestión Académica) — Django backend for a music conservatory. Manages students, teachers, subjects, enrollments, grades, and attendance. Has a Flutter mobile app (`mobile_app/`) and a GraphQL API (`/graphql/`). Django project name is `music_registry`.

## Commands

All commands run inside Docker unless specified.

```bash
# Start services
docker compose up --build

# Django management (standard workflow)
docker compose exec web python manage.py migrate
docker compose exec web python manage.py check
docker compose exec web python manage.py createsuperuser

# ETL — main data import (idempotent, always prefer this over individual import scripts)
docker compose exec web python manage.py etl_import_json --base-dir base_de_datos_json --ciclo 2025-2026
docker compose exec web python manage.py etl_import_json --base-dir base_de_datos_json --ciclo 2025-2026 --dry-run
docker compose exec web python manage.py etl_import_json --base-dir base_de_datos_json --ciclo 2025-2026 --create-student-users

# Dedup subjects (run after ETL if needed)
docker compose exec web python manage.py dedupe_subjects --apply

# Legacy data migration (only if legacy Grade/Attendance rows exist)
docker compose exec web python manage.py migrate_legacy_grades
docker compose exec web python manage.py migrate_legacy_attendance

# Run tests
docker compose exec web python manage.py test

# Run a single test
docker compose exec web python manage.py test academia.tests.MyTestCase
```

## Architecture

### Django Apps

| App | Role |
|-----|------|
| `users` | Central domain model (`Usuario`), auth backend, GraphQL queries/schema, login views |
| `students` | `Student` profile extending `Usuario` |
| `teachers` | `Teacher` profile extending `Usuario` |
| `subjects` | `Subject` model (`INSTRUMENTO`, `TEORIA`, `AGRUPACION`) |
| `classes` | `GradeLevel`, `Clase`, `Enrollment`, grading (`CalificacionParcial`), attendance (`Asistencia`), homework (`Deber`/`DeberEntrega`) |
| `academia` | REST API views and serializers |

### Key Design: Unified `users.Usuario`

`Usuario` is the single domain identity — not Django's `auth.User`. Django's `User` links to it optionally via `Usuario.auth_user` (OneToOne). All person data (nombre, email, cedula, phone) lives in `Usuario`. `Student` and `Teacher` are profiles that extend it with OneToOne.

Role-based access: `Usuario.rol` is `DOCENTE`, `ESTUDIANTE`, or `PENDIENTE`.

### Two Middleware (currently disabled for GraphQL migration)

`AttachUsuarioProfilesMiddleware` and `ForcePasswordChangeMiddleware` are commented out in `settings.py`. Re-enable when GraphQL migration is complete.

### GraphQL

Endpoint: `/graphql/` (uses `AnonymousGraphQLView` — no auth required during migration phase).  
Schema: `music_registry/schema.py` composes queries from `users/graphql/queries.py` and mutations inline.  
GraphiQL available in DEBUG mode.

### REST API

Token + Session auth via DRF. Endpoints under `/api/` (routed from `users/api/urls.py`) and `/academia/`.

### Data Model (key relationships)

```
Usuario (1) ─── (1) Student ── (N) Enrollment ── (1) Clase ── (1) Subject
        (1) ─── (1) Teacher
Enrollment also carries: docente (Usuario FK) — critical for instrument classes
CalificacionParcial links Student + Subject + TipoAporte + quimestre/parcial fields
```

### ETL Pipeline

Source data: Excel files → JSON in `archivos_formularios/base_de_datos_json/` → DB via `etl_import_json` management command.

Individual legacy import scripts (`import_subjects`, `import_teachers`, `import_students`) now just delegate to `etl_import_json`. Do not use them directly.

GraphQL-based migration scripts live in `migraciones/` (e.g., `graphql_migrate.py`).

### In-Progress: Legacy → New Model Migration

`Grade` and `Attendance` (legacy models in `classes/models.py`) coexist with the new `Enrollment`/`Asistencia`/`CalificacionParcial` system. Some views in `teachers/views.py` and `students/views.py` still use legacy field names (`Clase.teacher`, `Enrollment.student`, `Student.name`). Do not remove legacy models until all views are migrated.

### Database

PostgreSQL in Docker (`music_registry_db`). Configured via env vars: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`. Defaults match `docker-compose.yml` service names.

### Flutter Mobile App

Located in `mobile_app/`. Communicates with the Django backend. Developed via the `flutter_dev` Docker service.
