"""Pytest fixtures for streaming market data tests."""

import sys
from pathlib import Path
from typing import List

import pytest


def pytest_configure(config):
    """Register custom marks."""
    config.addinivalue_line("markers", "integration: mark test as integration (requires PostgreSQL)")

# Project root (tests/streaming_market_data -> parent.parent = tests, parent.parent.parent = project root)
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from streaming_market_data.models import QuoteSnapshot, TickRecord
from streaming_market_data.interfaces import IMarketDataRepository

try:
    from streaming_market_data.streaming.client import MarketDataCallbackHandler
except ImportError:
    MarketDataCallbackHandler = None


class InMemoryMarketDataRepository(IMarketDataRepository):
    """In-memory repository for unit tests."""

    def __init__(self):
        self.ticks: List[TickRecord] = []
        self.snapshots: List[QuoteSnapshot] = []

    def insert_ticks(self, ticks: List[TickRecord]) -> None:
        self.ticks.extend(ticks)

    def insert_snapshot(self, snapshot: QuoteSnapshot) -> None:
        self.snapshots.append(snapshot)


@pytest.fixture
def in_memory_repo():
    """In-memory repository for unit tests."""
    return InMemoryMarketDataRepository()


@pytest.fixture
def callback_handler(in_memory_repo):
    """Callback handler backed by in-memory repository."""
    if MarketDataCallbackHandler is None:
        pytest.importorskip("ibapi")
    return MarketDataCallbackHandler(in_memory_repo)


@pytest.fixture
def sample_tick_record():
    """Sample TickRecord for tests."""
    from datetime import datetime, timezone
    return TickRecord(
        req_id=700001,
        symbol="AAPL",
        sec_type="STK",
        exchange="SMART",
        tick_type="Last",
        time_utc=datetime.now(timezone.utc),
        price=150.25,
        size=100,
        bid_price=None,
        ask_price=None,
        bid_size=None,
        ask_size=None,
    )


@pytest.fixture
def sample_quote_snapshot():
    """Sample QuoteSnapshot for tests."""
    from datetime import datetime, timezone
    return QuoteSnapshot(
        req_id=700002,
        symbol="AAPL",
        sec_type="STK",
        exchange="SMART",
        bid=150.20,
        ask=150.30,
        last=150.25,
        bid_size=200,
        ask_size=100,
        last_size=100,
        volume=1_000_000,
        snapshot_time_utc=datetime.now(timezone.utc),
    )


@pytest.fixture
def test_db_url():
    """Test database URL from env or default local."""
    import os
    return (
        os.getenv("STREAMING_MARKET_DATA_TEST_DB_URL")
        or os.getenv("DATABASE_URL")
        or "postgresql://localhost:5432/ib_streaming_test"
    )
