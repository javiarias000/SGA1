.PHONY: help up down build migrate shell test etl-dry etl wa-logs api-logs

.DEFAULT_GOAL := help

API     = docker compose exec api
MANAGE  = $(API) python manage.py

help:
	@echo "SGA1 — Sistema de Gestión Académica"
	@echo "===================================="
	@echo ""
	@echo "Servicios:"
	@echo "  make up            - Levantar todos los servicios"
	@echo "  make down          - Detener todos los servicios"
	@echo "  make build         - Reconstruir imágenes"
	@echo "  make ps            - Estado de contenedores"
	@echo ""
	@echo "Django (API):"
	@echo "  make migrate       - Correr migraciones"
	@echo "  make shell         - Django shell"
	@echo "  make check         - Verificar configuración"
	@echo "  make test          - Correr tests"
	@echo ""
	@echo "ETL:"
	@echo "  make etl-dry       - ETL conservatorio.db (dry-run)"
	@echo "  make etl           - ETL conservatorio.db (real)"
	@echo ""
	@echo "Logs:"
	@echo "  make api-logs      - Logs del servicio API"
	@echo "  make wa-logs       - Logs del servicio WhatsApp"

# ── Docker ──────────────────────────────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

ps:
	docker compose ps

# ── Django API ───────────────────────────────────────────────────────────────
migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

shell:
	$(MANAGE) shell

check:
	$(MANAGE) check

test:
	$(API) python -m pytest -v

collectstatic:
	$(MANAGE) collectstatic --noinput

# ── ETL ──────────────────────────────────────────────────────────────────────
etl-dry:
	$(MANAGE) import_from_conservatorio_db --db /whatsapp/conservatorio.db --dry-run

etl:
	$(MANAGE) import_from_conservatorio_db --db /whatsapp/conservatorio.db

# ── Logs ─────────────────────────────────────────────────────────────────────
api-logs:
	docker compose logs -f api

wa-logs:
	docker compose logs -f whatsapp

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
