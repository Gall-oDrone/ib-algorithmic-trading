"""Unit tests for corporate data client and callback handler."""

from unittest.mock import MagicMock

import pytest
from ibapi.contract import Contract

from corporate_data.exceptions import (
    CorporateDataConfigurationError,
    CorporateDataRequestIdExhaustedError,
)
from corporate_data.wsh.client import (
    CorporateDataCallbackHandler,
    IBCorporateDataClient,
    next_corporate_req_id,
)


SAMPLE_WSH_JSON = '{"conId": 265598, "events": [{"event_type": "wshe_dividend"}]}'


@pytest.fixture
def mock_ib_client():
    client = MagicMock()
    client.isConnected = MagicMock(return_value=True)
    client.reqWshEventData = MagicMock()
    client.cancelWshEventData = MagicMock()
    return client


def test_callback_handler_persists_parsed_event(in_memory_corporate_repo):
    handler = CorporateDataCallbackHandler(in_memory_corporate_repo)
    handler.register_request(900001, "AAPL", "STK", "SMART", {"conId": 265598})

    handler.wsh_event_data(900001, SAMPLE_WSH_JSON)

    assert len(in_memory_corporate_repo.events) == 1
    event = in_memory_corporate_repo.events[0]
    assert event.symbol == "AAPL"
    assert event.filter_payload["conId"] == 265598
    assert event.json_payload["events"][0]["event_type"] == "wshe_dividend"


def test_request_wsh_event_data_calls_ibapi(mock_ib_client, in_memory_corporate_repo):
    handler = CorporateDataCallbackHandler(in_memory_corporate_repo)
    client = IBCorporateDataClient(mock_ib_client, handler)

    contract = Contract()
    contract.symbol = "AAPL"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

    payload = {"conId": 265598, "filter": "wshe_div|wshe_split"}
    client.request_wsh_event_data(900002, contract, payload)
    mock_ib_client.reqWshEventData.assert_called_once()
    args = mock_ib_client.reqWshEventData.call_args[0]
    assert args[0] == 900002
    assert args[1].conId == 265598
    assert args[1].filter == "wshe_div|wshe_split"


def test_request_wsh_event_data_requires_connection(mock_ib_client, in_memory_corporate_repo):
    mock_ib_client.isConnected.return_value = False
    handler = CorporateDataCallbackHandler(in_memory_corporate_repo)
    client = IBCorporateDataClient(mock_ib_client, handler)

    contract = Contract()
    contract.symbol = "AAPL"
    contract.secType = "STK"
    contract.exchange = "SMART"

    with pytest.raises(CorporateDataConfigurationError, match="not connected"):
        client.request_wsh_event_data(900003, contract, {"conId": 265598})


def test_cancel_wsh_event_data_calls_ibapi(mock_ib_client, in_memory_corporate_repo):
    handler = CorporateDataCallbackHandler(in_memory_corporate_repo)
    client = IBCorporateDataClient(mock_ib_client, handler)
    client.cancel_wsh_event_data(900004)
    mock_ib_client.cancelWshEventData.assert_called_once_with(900004)


def test_request_wsh_event_data_batch_submits_multiple_requests(
    mock_ib_client, in_memory_corporate_repo
):
    handler = CorporateDataCallbackHandler(in_memory_corporate_repo)
    client = IBCorporateDataClient(mock_ib_client, handler)

    c1 = Contract()
    c1.symbol = "AAPL"
    c1.secType = "STK"
    c1.exchange = "SMART"

    c2 = Contract()
    c2.symbol = "TSLA"
    c2.secType = "STK"
    c2.exchange = "SMART"

    client.request_wsh_event_data_batch(
        [
            {"req_id": 900010, "contract": c1, "filter_payload": {"conId": 265598}},
            {"req_id": 900011, "contract": c2, "filter_payload": {"conId": 76792991}},
        ]
    )

    assert mock_ib_client.reqWshEventData.call_count == 2


def test_on_ib_error_untracks_request_for_missing_subscription(in_memory_corporate_repo):
    handler = CorporateDataCallbackHandler(in_memory_corporate_repo)
    handler.register_request(900005, "AAPL", "STK", "SMART", {"conId": 265598})
    handler.on_ib_error(900005, 10276, "No market data permissions for WSH")
    handler.wsh_event_data(900005, SAMPLE_WSH_JSON)
    assert len(in_memory_corporate_repo.events) == 0


def test_next_corporate_req_id_returns_incrementing_ids():
    if hasattr(next_corporate_req_id, "_counter"):
        del next_corporate_req_id._counter
    a = next_corporate_req_id()
    b = next_corporate_req_id()
    assert b == a + 1
    assert a >= 900000


def test_next_corporate_req_id_exhaustion():
    next_corporate_req_id._counter = 999999
    with pytest.raises(CorporateDataRequestIdExhaustedError):
        next_corporate_req_id()
