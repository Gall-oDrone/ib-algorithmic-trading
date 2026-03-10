"""Unit tests for TickRecord and QuoteSnapshot."""

from datetime import datetime, timezone

import pytest

from streaming_market_data.models import QuoteSnapshot, TickRecord


def test_tick_record_creation():
    t = datetime.now(timezone.utc)
    r = TickRecord(
        req_id=1,
        symbol="AAPL",
        sec_type="STK",
        exchange="SMART",
        tick_type="Last",
        time_utc=t,
        price=100.0,
        size=50,
    )
    assert r.req_id == 1
    assert r.symbol == "AAPL"
    assert r.tick_type == "Last"
    assert r.price == 100.0
    assert r.size == 50


def test_tick_record_bid_ask():
    t = datetime.now(timezone.utc)
    r = TickRecord(
        req_id=2,
        symbol="GOOG",
        sec_type="STK",
        exchange="NASDAQ",
        tick_type="BidAsk",
        time_utc=t,
        bid_price=140.1,
        ask_price=140.2,
        bid_size=10,
        ask_size=20,
    )
    assert r.tick_type == "BidAsk"
    assert r.bid_price == 140.1
    assert r.ask_size == 20


def test_tick_record_invalid_tick_type():
    with pytest.raises(ValueError, match="tick_type must be one of"):
        TickRecord(
            req_id=1,
            symbol="AAPL",
            sec_type="STK",
            exchange="SMART",
            tick_type="Invalid",
            time_utc=datetime.now(timezone.utc),
        )


def test_tick_record_equality():
    t = datetime.now(timezone.utc)
    r1 = TickRecord(1, "A", "STK", "SMART", "Last", t, 1.0, 1)
    r2 = TickRecord(1, "A", "STK", "SMART", "Last", t, 1.0, 1)
    assert r1 == r2


def test_quote_snapshot_creation():
    t = datetime.now(timezone.utc)
    s = QuoteSnapshot(
        req_id=1,
        symbol="AAPL",
        sec_type="STK",
        exchange="SMART",
        bid=99.0,
        ask=101.0,
        last=100.0,
        bid_size=100,
        ask_size=200,
        last_size=50,
        volume=1_000_000,
        snapshot_time_utc=t,
    )
    assert s.req_id == 1
    assert s.symbol == "AAPL"
    assert s.bid == 99.0
    assert s.volume == 1_000_000


def test_quote_snapshot_optional_fields():
    s = QuoteSnapshot(
        req_id=1,
        symbol="X",
        sec_type="STK",
        exchange="SMART",
    )
    assert s.bid is None
    assert s.ask is None
    assert s.last is None
