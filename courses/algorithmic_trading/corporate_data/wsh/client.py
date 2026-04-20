"""IB client facade and callback handler for reqWshEventData."""

from datetime import datetime, timezone
from typing import Any, Dict, List

from ibapi.common import WshEventData
from ibapi.contract import Contract
from ibapi.server_versions import MIN_SERVER_VER_WSH_EVENT_DATA_FILTERS_DATE

from corporate_data.exceptions import (
    CorporateDataConfigurationError,
    CorporateDataRequestIdExhaustedError,
    CorporateDataStorageError,
)
from corporate_data.interfaces import ICorporateDataClient, ICorporateDataRepository
from corporate_data.models import WshEventRecord
from corporate_data.parsers import parse_wsh_json, parse_wsh_json_string, parse_wsh_yaml

try:
    from utils import get_logger
except ImportError:
    import logging

    def get_logger(name: str):
        return logging.getLogger(name or __name__)


logger = get_logger(__name__)

_CORPORATE_REQ_ID_BASE = 900000
_MAX_REQ_IDS = 100000
_ERROR_CODE_NO_SUBSCRIPTION = 10276


class CorporateDataCallbackHandler:
    """Handle EWrapper.wshEventData callback and persist parsed payloads."""

    def __init__(self, repository: ICorporateDataRepository):
        self._repository = repository
        self._req_info: Dict[int, Dict[str, Any]] = {}

    def register_request(
        self,
        req_id: int,
        symbol: str,
        sec_type: str,
        exchange: str,
        filter_payload: Dict[str, Any],
    ) -> None:
        self._req_info[req_id] = {
            "symbol": symbol,
            "sec_type": sec_type,
            "exchange": exchange,
            "filter_payload": dict(filter_payload),
        }

    def unregister(self, req_id: int) -> None:
        self._req_info.pop(req_id, None)

    def on_ib_error(self, req_id: int, error_code: int, error_msg: str) -> None:
        """Handle IB errors for tracked WSH requests."""
        if req_id not in self._req_info:
            return
        if error_code == _ERROR_CODE_NO_SUBSCRIPTION:
            logger.warning(
                "WSH entitlement missing for req_id=%s: %s",
                req_id,
                error_msg,
            )
            self.unregister(req_id)

    def wsh_event_data(self, req_id: int, data_json: str) -> None:
        info = self._req_info.get(req_id)
        if not info:
            return

        normalized_json = parse_wsh_json_string(data_json)
        json_payload = parse_wsh_json(normalized_json)
        yaml_payload = parse_wsh_yaml(normalized_json)

        event = WshEventRecord(
            req_id=req_id,
            symbol=info["symbol"],
            sec_type=info["sec_type"],
            exchange=info["exchange"],
            filter_payload=info["filter_payload"],
            raw_json=normalized_json,
            json_payload=json_payload,
            yaml_payload=yaml_payload,
            received_at_utc=datetime.now(timezone.utc),
        )
        try:
            self._repository.insert_event(event)
        except Exception as e:
            logger.exception("insert_event failed for req_id=%s: %s", req_id, e)
            raise CorporateDataStorageError(f"insert_event failed for req_id={req_id}: {e}") from e
        finally:
            self.unregister(req_id)


class IBCorporateDataClient(ICorporateDataClient):
    """Wrap EClient reqWshEventData/cancelWshEventData calls."""

    def __init__(self, client: Any, callback_handler: CorporateDataCallbackHandler):
        self._client = client
        self._handler = callback_handler

    def _ensure_connected(self) -> None:
        try:
            connected = bool(self._client.isConnected())
        except Exception:
            connected = False
        if not connected:
            raise CorporateDataConfigurationError(
                "IB API client is not connected. Start and log into TWS or IB Gateway "
                "before requesting corporate WSH data."
            )

    def request_wsh_event_data(
        self,
        req_id: int,
        contract: Contract,
        filter_payload: Dict[str, Any],
    ) -> None:
        self._ensure_connected()
        if not isinstance(filter_payload, dict):
            raise ValueError("filter_payload must be a dictionary")

        self._handler.register_request(
            req_id=req_id,
            symbol=contract.symbol,
            sec_type=contract.secType,
            exchange=contract.exchange or "",
            filter_payload=filter_payload,
        )
        wsh_event_data = WshEventData()
        wsh_event_data.conId = int(filter_payload.get("conId", 0))
        wsh_event_data.filter = str(filter_payload.get("filter", ""))
        wsh_event_data.fillWatchlist = bool(filter_payload.get("fillWatchlist", False))
        wsh_event_data.fillPortfolio = bool(filter_payload.get("fillPortfolio", False))
        wsh_event_data.fillCompetitors = bool(filter_payload.get("fillCompetitors", False))
        wsh_event_data.startDate = str(filter_payload.get("startDate", ""))
        wsh_event_data.endDate = str(filter_payload.get("endDate", ""))
        wsh_event_data.totalLimit = int(filter_payload.get("totalLimit", 0))

        self._client.reqWshEventData(
            req_id,
            wsh_event_data,
            MIN_SERVER_VER_WSH_EVENT_DATA_FILTERS_DATE,
        )

    def cancel_wsh_event_data(self, req_id: int) -> None:
        self._client.cancelWshEventData(req_id)
        self._handler.unregister(req_id)

    def request_wsh_event_data_batch(self, requests: List[Dict[str, Any]]) -> None:
        """Submit multiple WSH requests as concurrent in-flight calls."""
        self._ensure_connected()
        for item in requests:
            self.request_wsh_event_data(
                req_id=item["req_id"],
                contract=item["contract"],
                filter_payload=item["filter_payload"],
            )


def next_corporate_req_id() -> int:
    """Return the next unique request ID for corporate WSH requests."""
    if not hasattr(next_corporate_req_id, "_counter"):
        next_corporate_req_id._counter = _CORPORATE_REQ_ID_BASE
    next_corporate_req_id._counter += 1
    if next_corporate_req_id._counter >= _CORPORATE_REQ_ID_BASE + _MAX_REQ_IDS:
        raise CorporateDataRequestIdExhaustedError("Corporate request ID pool exhausted")
    return next_corporate_req_id._counter
