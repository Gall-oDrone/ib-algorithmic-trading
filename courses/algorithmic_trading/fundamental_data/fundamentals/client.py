"""IB client facade and callback handler for reqFundamentalData."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ibapi.contract import Contract
from ibapi.tag_value import TagValue

from fundamental_data.exceptions import (
    FundamentalDataConfigurationError,
    FundamentalDataRequestIdExhaustedError,
    FundamentalDataStorageError,
)
from fundamental_data.interfaces import IFundamentalDataClient, IFundamentalDataRepository
from fundamental_data.models import FundamentalReportRecord
from fundamental_data.parsers import parse_to_json, parse_to_xml_string, parse_to_yaml

try:
    from utils import get_logger
except ImportError:
    import logging

    def get_logger(name: str):
        return logging.getLogger(name or __name__)


logger = get_logger(__name__)

_FUNDAMENTAL_REQ_ID_BASE = 800000
_MAX_REQ_IDS = 100000
_SUPPORTED_REPORT_TYPES = {
    "ReportSnapshot",
    "ReportsFinSummary",
    "ReportRatios",
    "ReportsFinStatements",
    "RESC",
    "CalendarReport",
}


class FundamentalDataCallbackHandler:
    """Handle EWrapper.fundamentalData callback and persist parsed payloads."""

    def __init__(self, repository: IFundamentalDataRepository):
        self._repository = repository
        self._req_info: Dict[int, Dict[str, str]] = {}

    def register_request(
        self,
        req_id: int,
        symbol: str,
        sec_type: str,
        exchange: str,
        report_type: str,
    ) -> None:
        self._req_info[req_id] = {
            "symbol": symbol,
            "sec_type": sec_type,
            "exchange": exchange,
            "report_type": report_type,
        }

    def unregister(self, req_id: int) -> None:
        self._req_info.pop(req_id, None)

    def fundamental_data(self, req_id: int, data: str) -> None:
        info = self._req_info.get(req_id)
        if not info:
            return

        xml_payload = parse_to_xml_string(data)
        json_payload = parse_to_json(xml_payload)
        yaml_payload = parse_to_yaml(xml_payload)

        report = FundamentalReportRecord(
            req_id=req_id,
            symbol=info["symbol"],
            sec_type=info["sec_type"],
            exchange=info["exchange"],
            report_type=info["report_type"],
            xml_payload=xml_payload,
            json_payload=json_payload,
            yaml_payload=yaml_payload,
            received_at_utc=datetime.now(timezone.utc),
        )
        try:
            self._repository.insert_report(report)
        except Exception as e:
            logger.exception("insert_report failed for req_id=%s: %s", req_id, e)
            raise FundamentalDataStorageError(f"insert_report failed for req_id={req_id}: {e}") from e
        finally:
            self.unregister(req_id)


class IBFundamentalDataClient(IFundamentalDataClient):
    """Wrap EClient reqFundamentalData/cancelFundamentalData calls."""

    def __init__(self, client: Any, callback_handler: FundamentalDataCallbackHandler):
        self._client = client
        self._handler = callback_handler

    def _ensure_connected(self) -> None:
        try:
            connected = bool(self._client.isConnected())
        except Exception:
            connected = False
        if not connected:
            raise FundamentalDataConfigurationError(
                "IB API client is not connected. Start and log into TWS or IB Gateway "
                "before requesting fundamental data."
            )

    def request_fundamental_data(
        self,
        req_id: int,
        contract: Contract,
        report_type: str = "ReportSnapshot",
        fundamental_data_options: Optional[List[TagValue]] = None,
    ) -> None:
        self._ensure_connected()
        if report_type not in _SUPPORTED_REPORT_TYPES:
            raise ValueError(
                f"Unsupported report_type '{report_type}'. "
                f"Supported: {sorted(_SUPPORTED_REPORT_TYPES)}"
            )

        options = fundamental_data_options or []
        self._handler.register_request(
            req_id=req_id,
            symbol=contract.symbol,
            sec_type=contract.secType,
            exchange=contract.exchange or "",
            report_type=report_type,
        )
        self._client.reqFundamentalData(req_id, contract, report_type, options)

    def cancel_fundamental_data(self, req_id: int) -> None:
        self._client.cancelFundamentalData(req_id)
        self._handler.unregister(req_id)

    def request_fundamental_data_batch(
        self,
        requests: List[Dict[str, Any]],
    ) -> None:
        """Submit multiple fundamental requests as concurrent in-flight calls."""
        self._ensure_connected()
        for item in requests:
            self.request_fundamental_data(
                req_id=item["req_id"],
                contract=item["contract"],
                report_type=item.get("report_type", "ReportSnapshot"),
                fundamental_data_options=item.get("fundamental_data_options"),
            )


def next_fundamental_req_id() -> int:
    """Return the next unique request ID for fundamental data requests."""
    if not hasattr(next_fundamental_req_id, "_counter"):
        next_fundamental_req_id._counter = _FUNDAMENTAL_REQ_ID_BASE
    next_fundamental_req_id._counter += 1
    if next_fundamental_req_id._counter >= _FUNDAMENTAL_REQ_ID_BASE + _MAX_REQ_IDS:
        raise FundamentalDataRequestIdExhaustedError("Fundamental request ID pool exhausted")
    return next_fundamental_req_id._counter
