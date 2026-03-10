"""PostgreSQL implementation of IMarketDataRepository."""

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional

from streaming_market_data.exceptions import StorageError
from streaming_market_data.interfaces import IMarketDataRepository
from streaming_market_data.models import QuoteSnapshot, TickRecord


def _to_ts(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@contextmanager
def _connection(database_url: str):
    import psycopg2
    conn = psycopg2.connect(database_url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class PostgresMarketDataRepository(IMarketDataRepository):
    """PostgreSQL repository for ticks and snapshots. Uses env/config for connection."""

    def __init__(self, database_url: Optional[str] = None):
        self._database_url = (
            database_url
            or os.getenv("STREAMING_MARKET_DATA_DB_URL")
            or os.getenv("DATABASE_URL")
            or os.getenv("POSTGRES_URL")
            or "postgresql://localhost:5432/ib_streaming"
        )

    def insert_ticks(self, ticks: List[TickRecord]) -> None:
        if not ticks:
            return
        cols = [
            "req_id",
            "symbol",
            "sec_type",
            "exchange",
            "tick_type",
            "time_utc",
            "price",
            "size",
            "bid_price",
            "ask_price",
            "bid_size",
            "ask_size",
        ]
        template = (
            "INSERT INTO market_data_ticks ("
            + ", ".join(cols)
            + ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        rows = [
            (
                t.req_id,
                t.symbol,
                t.sec_type,
                t.exchange,
                t.tick_type,
                _to_ts(t.time_utc),
                t.price,
                t.size,
                t.bid_price,
                t.ask_price,
                t.bid_size,
                t.ask_size,
            )
            for t in ticks
        ]
        try:
            from psycopg2.extras import execute_batch
            with _connection(self._database_url) as conn:
                with conn.cursor() as cur:
                    execute_batch(cur, template, rows)
        except Exception as e:
            raise StorageError(f"insert_ticks failed: {e}") from e

    def insert_snapshot(self, snapshot: QuoteSnapshot) -> None:
        cols = [
            "req_id",
            "symbol",
            "sec_type",
            "exchange",
            "bid",
            "ask",
            "last",
            "bid_size",
            "ask_size",
            "last_size",
            "volume",
            "snapshot_time_utc",
        ]
        template = (
            "INSERT INTO market_data_snapshots ("
            + ", ".join(cols)
            + ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        row = (
            snapshot.req_id,
            snapshot.symbol,
            snapshot.sec_type,
            snapshot.exchange,
            snapshot.bid,
            snapshot.ask,
            snapshot.last,
            snapshot.bid_size,
            snapshot.ask_size,
            snapshot.last_size,
            snapshot.volume,
            _to_ts(snapshot.snapshot_time_utc),
        )
        try:
            with _connection(self._database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(template, row)
        except Exception as e:
            raise StorageError(f"insert_snapshot failed: {e}") from e
