"""Integration tests for PostgresMarketDataRepository (requires local PostgreSQL)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

try:
    import psycopg2
    from psycopg2 import OperationalError
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False

from streaming_market_data.models import QuoteSnapshot, TickRecord
from streaming_market_data.storage.postgres_repository import PostgresMarketDataRepository


pytestmark = pytest.mark.skipif(not _PSYCOPG2_AVAILABLE, reason="psycopg2 not installed or not loadable")


def _run_schema(conn, schema_path: Path) -> None:
    with open(schema_path) as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def _truncate_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE market_data_ticks, market_data_snapshots RESTART IDENTITY")
    conn.commit()


@pytest.fixture
def postgres_repo(test_db_url):
    """Repository connected to test DB. Schema must exist (created once)."""
    return PostgresMarketDataRepository(database_url=test_db_url)


@pytest.fixture
def postgres_conn(test_db_url):
    """Raw connection for setup/teardown and assertions. Skips if DB unavailable."""
    try:
        conn = psycopg2.connect(test_db_url)
    except OperationalError as e:
        pytest.skip(f"PostgreSQL not available: {e}")
    schema_path = Path(__file__).resolve().parent.parent.parent / "streaming_market_data" / "storage" / "schema.sql"
    _run_schema(conn, schema_path)
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def truncate_after(postgres_conn):
    """Truncate tables after each test."""
    yield
    _truncate_tables(postgres_conn)


@pytest.mark.integration
def test_insert_snapshot_and_query(postgres_repo, postgres_conn):
    t = datetime.now(timezone.utc)
    snapshot = QuoteSnapshot(
        req_id=8001,
        symbol="AAPL",
        sec_type="STK",
        exchange="SMART",
        bid=150.0,
        ask=150.5,
        last=150.25,
        bid_size=100,
        ask_size=200,
        last_size=50,
        volume=1_000_000,
        snapshot_time_utc=t,
    )
    postgres_repo.insert_snapshot(snapshot)
    with postgres_conn.cursor() as cur:
        cur.execute(
            "SELECT req_id, symbol, bid, ask, last FROM market_data_snapshots WHERE req_id = %s",
            (8001,),
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] == 8001
    assert row[1] == "AAPL"
    assert float(row[2]) == 150.0
    assert float(row[3]) == 150.5
    assert float(row[4]) == 150.25


@pytest.mark.integration
def test_insert_ticks_and_query(postgres_repo, postgres_conn):
    t = datetime.now(timezone.utc)
    ticks = [
        TickRecord(
            req_id=8002,
            symbol="GOOG",
            sec_type="STK",
            exchange="NASDAQ",
            tick_type="Last",
            time_utc=t,
            price=140.5,
            size=25,
        ),
        TickRecord(
            req_id=8002,
            symbol="GOOG",
            sec_type="STK",
            exchange="NASDAQ",
            tick_type="Last",
            time_utc=t,
            price=140.6,
            size=10,
        ),
    ]
    postgres_repo.insert_ticks(ticks)
    with postgres_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*), symbol FROM market_data_ticks WHERE req_id = %s GROUP BY symbol",
            (8002,),
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] == 2
    assert row[1] == "GOOG"


@pytest.mark.integration
def test_insert_ticks_empty_list(postgres_repo, postgres_conn):
    postgres_repo.insert_ticks([])
    with postgres_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM market_data_ticks")
        assert cur.fetchone()[0] == 0


@pytest.mark.integration
def test_insert_snapshot_bid_ask_only(postgres_repo, postgres_conn):
    snapshot = QuoteSnapshot(
        req_id=8003,
        symbol="MSFT",
        sec_type="STK",
        exchange="NASDAQ",
        bid=300.0,
        ask=300.1,
        last=None,
        bid_size=None,
        ask_size=None,
        last_size=None,
        volume=None,
        snapshot_time_utc=None,
    )
    postgres_repo.insert_snapshot(snapshot)
    with postgres_conn.cursor() as cur:
        cur.execute(
            "SELECT symbol, bid, ask, last FROM market_data_snapshots WHERE req_id = %s",
            (8003,),
        )
        row = cur.fetchone()
    assert row[0] == "MSFT"
    assert float(row[1]) == 300.0
    assert float(row[2]) == 300.1
    assert row[3] is None
