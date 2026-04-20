.PHONY: help setup install migrate test test-coverage clean db-create db-drop db-reset db-full

.DEFAULT_GOAL := help

help:
	@echo "SGA1 - Sistema de Gestión Académica"
	@echo "===================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup       - Install dependencies and setup environment"
	@echo "  make install     - Install Python dependencies"
	@echo "  make venv        - Create virtual environment"
	@echo ""
	@echo "Database:"
	@echo "  make db-create   - Create PostgreSQL database"
	@echo "  make db-drop     - Drop PostgreSQL database"
	@echo "  make db-reset    - Reset database (drop & recreate)"
	@echo "  make migrate     - Run Django migrations"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run test suite"
	@echo "  make test-quick  - Run tests (fast, no coverage)"
	@echo "  make test-coverage - Run tests with coverage report"
	@echo ""
	@echo "Development:"
	@echo "  make runserver   - Start Django dev server"
	@echo "  make shell       - Start Django shell"
	@echo "  make clean       - Clean temporary files"
	@echo ""

venv:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip

install:
	pip install -r requirements.txt

setup: venv install
	cp .env.example .env
	@echo "Setup complete. Edit .env file as needed."

db-create:
	bash manage_db.sh create

db-drop:
	bash manage_db.sh drop

db-reset:
	bash manage_db.sh reset

migrate:
	python manage.py migrate

db-full:
	bash manage_db.sh full

test:
	python -m pytest -v

test-quick:
	python -m pytest -v --tb=short

test-coverage:
	python -m pytest --cov=. --cov-report=html --cov-report=term-missing

runserver:
	python manage.py runserver

shell:
	python manage.py shell

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info

check:
	python manage.py check

lint:
	flake8 . --exclude=.venv,migrations,tests --max-line-length=120

format:
	black . --exclude=.venv,migrations,tests

all: setup db-create migrate test

docs-build:
	@echo "Generating test coverage report..."
	python -m pytest --cov=. --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"
