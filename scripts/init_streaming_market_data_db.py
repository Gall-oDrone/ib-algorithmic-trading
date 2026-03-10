#!/usr/bin/env python3
"""
Create streaming market data database and tables if they do not exist.

Usage:
  python scripts/init_streaming_market_data_db.py [--test]
  STREAMING_MARKET_DATA_TEST_DB_URL=... python scripts/init_streaming_market_data_db.py --test

Uses env: PGHOST, PGPORT, PGUSER, PGPASSWORD (or POSTGRES_URL for admin connection).
Creates database from POSTGRES_URL or postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/postgres,
then applies schema to the target database(s): ib_streaming (always), ib_streaming_test (if --test).
"""

import argparse
import os
import sys
from pathlib import Path

# Project root (script in scripts/ -> parent = project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def get_admin_url() -> str:
    """URL to connect to default 'postgres' DB for creating databases."""
    url = os.getenv("POSTGRES_ADMIN_URL")
    if url:
        return url
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD", "")
    if password:
        return f"postgresql://{user}:{password}@{host}:{port}/postgres"
    return f"postgresql://{user}@{host}:{port}/postgres"


def get_target_url(database: str) -> str:
    """URL for the target database (same credentials as admin)."""
    url = os.getenv("POSTGRES_ADMIN_URL") or os.getenv("POSTGRES_URL")
    if url:
        # Replace path with target database name
        if "/postgres" in url or url.rstrip("/").endswith("postgres"):
            base = url.rsplit("/", 1)[0]
            return f"{base}/{database}"
        return url
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD", "")
    if password:
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    return f"postgresql://{user}@{host}:{port}/{database}"


def database_exists(conn, dbname: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        return cur.fetchone() is not None


def create_database_if_not_exists(admin_url: str, dbname: str) -> None:
    import psycopg2
    conn = psycopg2.connect(admin_url)
    conn.autocommit = True
    try:
        if database_exists(conn, dbname):
            print(f"Database '{dbname}' already exists.")
            return
        with conn.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{dbname}"')
        print(f"Created database '{dbname}'.")
    finally:
        conn.close()


def apply_schema(conn, schema_path: Path) -> None:
    with open(schema_path) as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"Applied schema from {schema_path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create streaming market data DB and tables if not exist.")
    parser.add_argument("--test", action="store_true", help="Also create ib_streaming_test and apply schema")
    args = parser.parse_args()

    try:
        import psycopg2
    except ImportError:
        print("psycopg2 is required. Install with: pip install psycopg2-binary", file=sys.stderr)
        return 1

    admin_url = get_admin_url()
    schema_path = PROJECT_ROOT / "streaming_market_data" / "storage" / "schema.sql"
    if not schema_path.exists():
        print(f"Schema not found: {schema_path}", file=sys.stderr)
        return 1

    databases = ["ib_streaming"]
    if args.test:
        databases.append("ib_streaming_test")

    for dbname in databases:
        create_database_if_not_exists(admin_url, dbname)
        target_url = get_target_url(dbname)
        conn = psycopg2.connect(target_url)
        try:
            apply_schema(conn, schema_path)
        finally:
            conn.close()

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
