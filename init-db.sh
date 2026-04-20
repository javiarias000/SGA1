#!/bin/bash

# PostgreSQL initialization script for SGA1
# Runs automatically on first container startup

set -e

echo "Initializing PostgreSQL..."

# Enable extensions if needed
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Enable useful extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

    -- Create indexes for common queries (optional)
    -- Add custom initialization here as needed
EOSQL

echo "PostgreSQL initialization complete!"
