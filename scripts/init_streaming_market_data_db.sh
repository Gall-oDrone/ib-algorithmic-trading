#!/usr/bin/env bash
# Create streaming market data database(s) and apply schema if not exist.
# Usage: PGPASSWORD=gallo ./scripts/init_streaming_market_data_db.sh [--test]
# Uses: PGHOST=localhost PGPORT=5432 PGUSER=postgres (override with env)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCHEMA_FILE="$PROJECT_ROOT/streaming_market_data/storage/schema.sql"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
export PGPASSWORD="${PGPASSWORD:-}"

if [[ ! -f "$SCHEMA_FILE" ]]; then
  echo "Schema not found: $SCHEMA_FILE" >&2
  exit 1
fi

create_db_and_schema() {
  local dbname="$1"
  if psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$dbname'" | grep -q 1; then
    echo "Database '$dbname' already exists."
  else
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -c "CREATE DATABASE \"$dbname\";"
    echo "Created database '$dbname'."
  fi
  psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$dbname" -f "$SCHEMA_FILE"
  echo "Applied schema to '$dbname'."
}

create_db_and_schema "ib_streaming"
if [[ "${1:-}" == "--test" ]]; then
  create_db_and_schema "ib_streaming_test"
fi
echo "Done."
