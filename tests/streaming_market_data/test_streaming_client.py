"""Unit tests for streaming client and callback handler (mocked EClient)."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from ibapi.contract import Contract
from ibapi.ticktype import TickTypeEnum

from streaming_market_data.streaming.client import (
    IBMarketDataStreamClient,
    MarketDataCallbackHandler,
    next_streaming_req_id,
)
from streaming_market_data.exceptions import RequestIdExhaustedError


@pytest.fixture
def mock_ecustomer_client():
    c = MagicMock()
    c.reqMktData = MagicMock()
    c.cancelMktData = MagicMock()
    c.reqTickByTickData = MagicMock()
    c.cancelTickByTickData = MagicMock()
    return c


def test_callback_handler_registers_and_persists_snapshot(in_memory_repo, callback_handler):
    callback_handler.register_snapshot_request(700001, "AAPL", "STK", "SMART")
    callback_handler.tick_price(700001, TickTypeEnum.BID, 100.0, None)
    callback_handler.tick_price(700001, TickTypeEnum.ASK, 101.0, None)
    callback_handler.tick_size(700001, TickTypeEnum.BID_SIZE, Decimal("200"))
    callback_handler.tick_size(700001, TickTypeEnum.ASK_SIZE, Decimal("100"))
    callback_handler.tick_snapshot_end(700001)
    assert len(in_memory_repo.snapshots) == 1
    s = in_memory_repo.snapshots[0]
    assert s.symbol == "AAPL"
    assert s.bid == 100.0
    assert s.ask == 101.0
    assert s.bid_size == 200
    assert s.ask_size == 100


def test_callback_handler_tick_by_tick_all_last(in_memory_repo, callback_handler):
    callback_handler.register_tick_by_tick_request(700002, "GOOG", "STK", "NASDAQ", "Last")
    callback_handler.tick_by_tick_all_last(
        700002, 0, 1609459200000, 150.5, Decimal("25"), None, "NASDAQ", ""
    )
    assert len(in_memory_repo.ticks) == 1
    t = in_memory_repo.ticks[0]
    assert t.symbol == "GOOG"
    assert t.tick_type == "Last"
    assert t.price == 150.5
    assert t.size == 25


def test_callback_handler_tick_by_tick_bid_ask(in_memory_repo, callback_handler):
    callback_handler.register_tick_by_tick_request(700003, "MSFT", "STK", "NASDAQ", "BidAsk")
    callback_handler.tick_by_tick_bid_ask(
        700003, 1609459200000, 300.1, 300.2, Decimal("10"), Decimal("20"), None
    )
    assert len(in_memory_repo.ticks) == 1
    t = in_memory_repo.ticks[0]
    assert t.tick_type == "BidAsk"
    assert t.bid_price == 300.1
    assert t.ask_price == 300.2
    assert t.bid_size == 10
    assert t.ask_size == 20


def test_callback_handler_tick_by_tick_mid_point(in_memory_repo, callback_handler):
    callback_handler.register_tick_by_tick_request(700004, "SPY", "STK", "ARCA", "MidPoint")
    callback_handler.tick_by_tick_mid_point(700004, 1609459200000, 450.5)
    assert len(in_memory_repo.ticks) == 1
    t = in_memory_repo.ticks[0]
    assert t.tick_type == "MidPoint"
    assert t.price == 450.5


def test_ib_client_request_snapshot_calls_ecustomer(mock_ecustomer_client, callback_handler):
    client = IBMarketDataStreamClient(mock_ecustomer_client, callback_handler)
    contract = Contract()
    contract.symbol = "AAPL"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"
    client.request_snapshot(700010, contract, regulatory_snapshot=False)
    mock_ecustomer_client.reqMktData.assert_called_once()
    args = mock_ecustomer_client.reqMktData.call_args[0]
    assert args[0] == 700010
    assert args[2] == ""  # genericTickList
    assert args[3] is True  # snapshot
    assert args[4] is False  # regulatorySnapshot


def test_ib_client_request_tick_by_tick_calls_ecustomer(mock_ecustomer_client, callback_handler):
    client = IBMarketDataStreamClient(mock_ecustomer_client, callback_handler)
    contract = Contract()
    contract.symbol = "AAPL"
    contract.secType = "STK"
    contract.exchange = "SMART"
    client.request_tick_by_tick(700011, contract, tick_type="BidAsk", number_of_ticks=0, ignore_size=False)
    mock_ecustomer_client.reqTickByTickData.assert_called_once()
    args = mock_ecustomer_client.reqTickByTickData.call_args[0]
    assert args[0] == 700011
    assert args[2] == "BidAsk"


def test_ib_client_cancel_mkt_data(mock_ecustomer_client, callback_handler):
    client = IBMarketDataStreamClient(mock_ecustomer_client, callback_handler)
    client.cancel_mkt_data(700020)
    mock_ecustomer_client.cancelMktData.assert_called_once_with(700020)


def test_next_streaming_req_id_returns_incrementing_ids():
    # Reset counter for test
    if hasattr(next_streaming_req_id, "_counter"):
        del next_streaming_req_id._counter
    a = next_streaming_req_id()
    b = next_streaming_req_id()
    assert b == a + 1
    assert a >= 700000
