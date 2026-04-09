"""Unit tests for fundamental data client and callback handler."""

from unittest.mock import MagicMock

import pytest
from ibapi.contract import Contract

from fundamental_data.exceptions import (
    FundamentalDataConfigurationError,
    FundamentalDataRequestIdExhaustedError,
)
from fundamental_data.fundamentals.client import (
    FundamentalDataCallbackHandler,
    IBFundamentalDataClient,
    next_fundamental_req_id,
)


SAMPLE_XML = "<ReportSnapshot><Company><Name>Apple</Name></Company></ReportSnapshot>"


@pytest.fixture
def mock_ib_client():
    client = MagicMock()
    client.isConnected = MagicMock(return_value=True)
    client.reqFundamentalData = MagicMock()
    client.cancelFundamentalData = MagicMock()
    return client


def test_callback_handler_persists_parsed_report(in_memory_fundamental_repo):
    handler = FundamentalDataCallbackHandler(in_memory_fundamental_repo)
    handler.register_request(800001, "AAPL", "STK", "SMART", "ReportSnapshot")

    handler.fundamental_data(800001, SAMPLE_XML)

    assert len(in_memory_fundamental_repo.reports) == 1
    report = in_memory_fundamental_repo.reports[0]
    assert report.symbol == "AAPL"
    assert report.report_type == "ReportSnapshot"
    assert "ReportSnapshot" in report.json_payload
    assert "ReportSnapshot" in report.yaml_payload


def test_request_fundamental_data_calls_ibapi(mock_ib_client, in_memory_fundamental_repo):
    handler = FundamentalDataCallbackHandler(in_memory_fundamental_repo)
    client = IBFundamentalDataClient(mock_ib_client, handler)

    contract = Contract()
    contract.symbol = "AAPL"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

    client.request_fundamental_data(800002, contract, report_type="ReportSnapshot")
    mock_ib_client.reqFundamentalData.assert_called_once()
    args = mock_ib_client.reqFundamentalData.call_args[0]
    assert args[0] == 800002
    assert args[2] == "ReportSnapshot"


def test_request_fundamental_data_requires_connection(mock_ib_client, in_memory_fundamental_repo):
    mock_ib_client.isConnected.return_value = False
    handler = FundamentalDataCallbackHandler(in_memory_fundamental_repo)
    client = IBFundamentalDataClient(mock_ib_client, handler)

    contract = Contract()
    contract.symbol = "AAPL"
    contract.secType = "STK"
    contract.exchange = "SMART"

    with pytest.raises(FundamentalDataConfigurationError, match="not connected"):
        client.request_fundamental_data(800003, contract, report_type="ReportSnapshot")


def test_cancel_fundamental_data_calls_ibapi(mock_ib_client, in_memory_fundamental_repo):
    handler = FundamentalDataCallbackHandler(in_memory_fundamental_repo)
    client = IBFundamentalDataClient(mock_ib_client, handler)
    client.cancel_fundamental_data(800004)
    mock_ib_client.cancelFundamentalData.assert_called_once_with(800004)


def test_next_fundamental_req_id_returns_incrementing_ids():
    if hasattr(next_fundamental_req_id, "_counter"):
        del next_fundamental_req_id._counter
    a = next_fundamental_req_id()
    b = next_fundamental_req_id()
    assert b == a + 1
    assert a >= 800000


def test_next_fundamental_req_id_exhaustion():
    next_fundamental_req_id._counter = 899999
    with pytest.raises(FundamentalDataRequestIdExhaustedError):
        next_fundamental_req_id()
