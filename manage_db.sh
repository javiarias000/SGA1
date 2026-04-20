#!/bin/bash

# Script para gestionar base de datos PostgreSQL local

set -e

DB_NAME="${DB_NAME:-music_registry_db}"
DB_USER="${DB_USER:-music_user}"
DB_PASSWORD="${DB_PASSWORD:-music_password}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Verify PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    print_error "PostgreSQL is not installed. Install it first."
    exit 1
fi

# Verify Python/pip
if ! command -v python &> /dev/null; then
    print_error "Python is not installed."
    exit 1
fi

create_database() {
    print_info "Creating database '$DB_NAME'..."

    # Check if database exists
    if psql -h "$DB_HOST" -U postgres -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        print_warning "Database '$DB_NAME' already exists. Skipping..."
    else
        psql -h "$DB_HOST" -U postgres -c "CREATE DATABASE $DB_NAME;"
        print_info "Database '$DB_NAME' created."
    fi

    # Check if user exists
    if psql -h "$DB_HOST" -U postgres -c "\du" | grep -q "$DB_USER"; then
        print_warning "User '$DB_USER' already exists. Skipping..."
    else
        psql -h "$DB_HOST" -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
        print_info "User '$DB_USER' created."
    fi

    # Grant privileges
    psql -h "$DB_HOST" -U postgres -c "ALTER ROLE $DB_USER SUPERUSER;" || true
    psql -h "$DB_HOST" -U postgres -c "ALTER DATABASE $DB_NAME OWNER TO $DB_USER;" || true
    print_info "Privileges granted."
}

drop_database() {
    print_warning "Dropping database '$DB_NAME'..."

    if psql -h "$DB_HOST" -U postgres -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        psql -h "$DB_HOST" -U postgres -c "DROP DATABASE $DB_NAME;"
        print_info "Database '$DB_NAME' dropped."
    else
        print_warning "Database '$DB_NAME' does not exist."
    fi
}

reset_database() {
    print_warning "Resetting database..."
    drop_database
    create_database
}

migrate() {
    print_info "Running migrations..."
    python manage.py migrate
    print_info "Migrations completed."
}

run_tests() {
    print_info "Running tests..."
    python -m pytest --cov=. --cov-report=html --cov-report=term-missing
    print_info "Tests completed."
}

case "${1:-help}" in
    create)
        create_database
        ;;
    drop)
        drop_database
        ;;
    reset)
        reset_database
        ;;
    migrate)
        migrate
        ;;
    test)
        run_tests
        ;;
    full)
        reset_database
        migrate
        run_tests
        ;;
    *)
        echo "Usage: $0 {create|drop|reset|migrate|test|full}"
        echo ""
        echo "Commands:"
        echo "  create  - Create PostgreSQL database and user"
        echo "  drop    - Drop PostgreSQL database"
        echo "  reset   - Drop and recreate database"
        echo "  migrate - Run Django migrations"
        echo "  test    - Run test suite"
        echo "  full    - Reset, migrate, and test"
        echo ""
        echo "Environment variables:"
        echo "  DB_NAME=$DB_NAME"
        echo "  DB_USER=$DB_USER"
        echo "  DB_HOST=$DB_HOST"
        echo "  DB_PORT=$DB_PORT"
        exit 1
        ;;
esac
