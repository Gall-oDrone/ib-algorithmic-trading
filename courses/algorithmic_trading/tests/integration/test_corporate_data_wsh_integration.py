"""Integration test for WSH corporate data requests with a live TWS session."""

import json
import threading
import time

import pytest
from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.wrapper import EWrapper

from config import get_config
from corporate_data.wsh.client import (
    CorporateDataCallbackHandler,
    IBCorporateDataClient,
    next_corporate_req_id,
)


class _InMemoryEventRepo:
    def __init__(self):
        self.events = []

    def insert_event(self, event):
        self.events.append(event)


class WshIntegrationApp(EWrapper, EClient):
    """Thin wrapper that routes IB callbacks to CorporateDataCallbackHandler."""

    def __init__(self, handler: CorporateDataCallbackHandler):
        EClient.__init__(self, self)
        self._handler = handler
        self.connected = False
        self.entitlement_error = None
        self.last_error = None

    def nextValidId(self, orderId):
        self.connected = True

    def wshEventData(self, reqId, dataJson):
        self._handler.wsh_event_data(reqId, dataJson)

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        self.last_error = (reqId, errorCode, errorString)
        self._handler.on_ib_error(reqId, errorCode, errorString)
        if errorCode == 10276:
            self.entitlement_error = errorString


@pytest.mark.integration
def test_req_wsh_event_data_live_tws():
    """Requests WSH data from TWS; may skip when account lacks entitlements."""
    config = get_config()
    repo = _InMemoryEventRepo()
    handler = CorporateDataCallbackHandler(repo)
    app = WshIntegrationApp(handler)

    try:
        app.connect(config.host, config.port, clientId=3120)
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()
        time.sleep(3)

        if not app.isConnected():
            pytest.skip("Could not connect to TWS or IB Gateway.")

        client = IBCorporateDataClient(app, handler)
        contract = Contract()
        contract.symbol = "AAPL"
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        contract.conId = 265598

        req_id = next_corporate_req_id()
        filter_payload = {
            "conId": contract.conId,
            "filter": "wshe_ed|wshe_div|wshe_split",
            "fillWatchlist": False,
            "fillPortfolio": False,
            "startDate": "20260101",
            "endDate": "20261231",
            "totalLimit": 10,
        }
        client.request_wsh_event_data(req_id, contract, filter_payload)

        timeout = time.time() + 15
        while time.time() < timeout and not repo.events and not app.entitlement_error:
            time.sleep(0.25)

        if app.entitlement_error:
            pytest.skip(f"WSH entitlement missing in account: {app.entitlement_error}")

        if not repo.events:
            pytest.fail(
                "No WSH event payload received within timeout. "
                "Connection works, but account might not be entitled or no events matched filters."
            )

        event = repo.events[0]
        assert event.req_id == req_id
        assert event.symbol == "AAPL"
        assert isinstance(event.json_payload, dict)
        assert json.loads(event.raw_json) == event.json_payload
    finally:
        app.disconnect()
