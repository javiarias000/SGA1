# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## What this repo is
Server-rendered Django app (project: `music_registry/`) for an academic/music grading system.

Core stack:
- Django (`manage.py`, settings in `music_registry/settings.py`)
- PostgreSQL (default service in `docker-compose.yml`)
- Redis + Celery (tasks in `classes/tasks.py`, app wiring in `music_registry/celery.py`)
- Templates in `templates/` and app templates; static assets in `static/` (collected into `staticfiles/`)

## Common commands
Most contributors should use Docker Compose because the repo’s Docker image uses Python 3.12 (`dockerfile`) while local Python versions may differ.

### Run the app (Docker)
- Start web + Postgres + Redis (runs `collectstatic`, `migrate`, then `runserver`):
  - `docker compose up --build`
  - (older Compose): `docker-compose up --build`

### Django management
Run these against the `web` container:
- Migrations:
  - `docker compose exec web python manage.py migrate`
- Create admin user:
  - `docker compose exec web python manage.py createsuperuser`
- Django shell:
  - `docker compose exec web python manage.py shell`
- Collect static:
  - `docker compose exec web python manage.py collectstatic --noinput`

### Tests
This repo uses Django’s built-in test runner (no pytest config found).
- Run all tests:
  - `docker compose exec web python manage.py test`
- Run tests for one app:
  - `docker compose exec web python manage.py test students`
- Run a single test case or method (Django dotted path):
  - `docker compose exec web python manage.py test students.tests.SomeTestCase`
  - `docker compose exec web python manage.py test students.tests.SomeTestCase.test_something`

Note: several apps currently have placeholder `tests.py` files only.

### Celery
Celery is configured to use Redis (see `music_registry/settings.py` and `music_registry/celery.py`).
- Worker:
  - `docker compose exec web celery -A music_registry worker -l info`
- Beat scheduler (uses `app.conf.beat_schedule` in `music_registry/celery.py`):
  - `docker compose exec web celery -A music_registry beat -l info`

### Database access
- Open a `psql` session inside the DB container:
  - `docker compose exec db psql -U music_user -d music_registry_db`

(See `db_access_instructions.txt` for example inspection queries.)

### Data import / ETL commands
There are many custom management commands under `*/management/commands/` (primarily `classes/management/commands/` and `teachers/management/commands/`). The most “system-level” importer is:
- Idempotent ETL for JSON datasets (imports users/subjects/classes/enrollments):
  - `docker compose exec web python manage.py etl_import_json --base-dir base_de_datos_json --ciclo 2025-2026`
  - Optional flags: `--create-student-users`, `--dry-run`

Several other importers assume JSON files are available under `base_de_datos_json/` (mounted into the container by `docker-compose.yml`).

## High-level architecture (big picture)
### Django project entry points
- `music_registry/settings.py`: app registration, middleware, Postgres + Redis/Celery configuration, templates/static/media configuration.
- `music_registry/urls.py`: top-level URL routing.
- `music_registry/celery.py`: Celery app + scheduled tasks.

### Apps and responsibilities
- `users/`: authentication + dashboards routing.
  - Custom auth backend: `users/backends.py` (supports username or email; also tries `<username>@docentes.educacion.edu.ec`).
  - Middleware: `users/middleware.py` (forces password change via `users.models.Profile.must_change_password`).
- `teachers/`: teacher-facing UI (dashboard, grade entry, attendance, reports, homework tooling).
  - Main entry: `teachers/views.py` → `teacher_dashboard()` renders `teachers/dashboard_unified.html`.
  - Many endpoints are “template-driven” (server-rendered) plus a few JSON/AJAX endpoints under `teachers/api/...`.
- `students/`: student-facing UI (dashboard, classes/enrollment, grades, attendance, homework).
- `classes/`: domain models + shared logic.
  - Note: `classes/urls.py` is intentionally empty; the UI endpoints live in `teachers/` and `students/`.
  - Contains both legacy and newer “unified” grading/attendance models.
- `subjects/`: subject catalog.

### User model layers (important when refactoring)
There are three distinct “layers” in play:
- Django auth users: `django.contrib.auth.models.User` (login identity)
- Unified domain user: `users.models.Usuario` (academic domain identity with `rol`, and optional `auth_user` linkage)
- UI compatibility profiles:
  - `teachers.models.Teacher` links to both `auth_user` and optional `Usuario`
  - `students.models.Student` links to optional `auth_user` and optional `Usuario`

When changing relationships, check both the domain model (`Usuario`) and the compatibility profiles (`Student`/`Teacher`), as some views still assume the older shape.

### Grades + attendance: legacy vs unified
In `classes/models.py`:
- Legacy models kept for compatibility with existing views/templates:
  - `Grade` and `Attendance`
- Unified grading system:
  - `TipoAporte`, `CalificacionParcial`, and `PromedioCache`
  - `PromedioCache` is updated via signals on `CalificacionParcial` save/delete.

Additionally, there is a newer enrollment/attendance path:
- `Clase` + `Enrollment` (student–class–teacher association)
- `Calificacion` and `Asistencia` are modeled “per Enrollment”

Be careful: some views still use the legacy `Grade`/`Attendance` flow, while the teacher dashboard uses `CalificacionParcial` heavily.

### Access control and role routing
- `classes/middleware.py` (`RoleBasedAccessMiddleware`) uses path-prefix detection (`classes/routes.py`) plus presence of `request.user.teacher_profile` / `request.user.student_profile` to redirect users away from the wrong area.

## Project constraints (keep in mind)
This repo is actively working toward a unified dashboard/grade system:
- Preserve existing routes/templates and historical data while unifying models and UI.
- Maintain backward API compatibility; do not change DB schema without a migration.
- Prefer reversible, versioned migrations and avoid data loss.
- Remove dead/duplicate code only when you can prove it is unused (some “legacy” models are still referenced by templates/views).

## Notes / repo quirks
- The Docker build file is named `dockerfile` (lowercase). Docker Compose defaults to `Dockerfile`; this works on case-insensitive filesystems but may fail on case-sensitive ones. If build issues appear on Linux CI/hosts, consider renaming it to `Dockerfile` or updating `docker-compose.yml` to specify `dockerfile: dockerfile`.
- Root `package.json` contains only dependencies (no `scripts`). There is also a nested `teachers/static/teachers/package.json`; as of now, no build pipeline is configured in-repo for these JS deps, so treat them as experimental unless you confirm otherwise in templates/static usage.
