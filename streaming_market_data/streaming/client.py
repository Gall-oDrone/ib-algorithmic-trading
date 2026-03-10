"""IB client facade and callback handler for market data (reqMktData / tick-by-tick)."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from ibapi.common import TickAttrib, TickAttribBidAsk, TickAttribLast
from ibapi.contract import Contract
from ibapi.ticktype import TickTypeEnum

from streaming_market_data.exceptions import RequestIdExhaustedError
from streaming_market_data.interfaces import IMarketDataRepository, IMarketDataStreamClient
from streaming_market_data.models import QuoteSnapshot, TickRecord

try:
    from utils import get_logger
except ImportError:
    import logging
    def get_logger(name: str):
        return logging.getLogger(name or __name__)

logger = get_logger(__name__)

# Base for streaming req IDs to avoid clashing with order/historical IDs
_STREAMING_REQ_ID_BASE = 700000
_MAX_REQ_IDS = 100000


def _tick_type_to_field(tick_type: int) -> Optional[str]:
    m = {
        TickTypeEnum.BID: "bid",
        TickTypeEnum.ASK: "ask",
        TickTypeEnum.LAST: "last",
        TickTypeEnum.BID_SIZE: "bid_size",
        TickTypeEnum.ASK_SIZE: "ask_size",
        TickTypeEnum.LAST_SIZE: "last_size",
        TickTypeEnum.VOLUME: "volume",
    }
    return m.get(tick_type)


def _decimal_to_int(d: Any) -> Optional[int]:
    if d is None:
        return None
    if isinstance(d, Decimal):
        return int(d)
    return int(d)


def _decimal_to_float(d: Any) -> Optional[float]:
    if d is None:
        return None
    if isinstance(d, Decimal):
        return float(d)
    return float(d)


def _time_int_to_utc(time_int: int) -> datetime:
    """Convert IB time (ms since epoch) to timezone-aware UTC datetime."""
    return datetime.fromtimestamp(time_int / 1000.0, tz=timezone.utc)


class MarketDataCallbackHandler:
    """Handles EWrapper market data callbacks: builds TickRecord/QuoteSnapshot and writes to repository."""

    def __init__(self, repository: IMarketDataRepository):
        self._repository = repository
        self._req_info: Dict[int, Dict[str, Any]] = {}  # req_id -> {symbol, sec_type, exchange, snapshot_state, tick_type}
        self._snapshot_state: Dict[int, Dict[str, Any]] = {}  # req_id -> {bid, ask, last, bid_size, ask_size, last_size, volume}

    def register_snapshot_request(
        self,
        req_id: int,
        symbol: str,
        sec_type: str,
        exchange: str,
    ) -> None:
        self._req_info[req_id] = {
            "symbol": symbol,
            "sec_type": sec_type,
            "exchange": exchange,
            "mode": "snapshot",
        }
        self._snapshot_state[req_id] = {}

    def register_streaming_request(
        self,
        req_id: int,
        symbol: str,
        sec_type: str,
        exchange: str,
    ) -> None:
        self._req_info[req_id] = {
            "symbol": symbol,
            "sec_type": sec_type,
            "exchange": exchange,
            "mode": "streaming",
        }
        self._snapshot_state[req_id] = {}

    def register_tick_by_tick_request(
        self,
        req_id: int,
        symbol: str,
        sec_type: str,
        exchange: str,
        tick_type: str,
    ) -> None:
        self._req_info[req_id] = {
            "symbol": symbol,
            "sec_type": sec_type,
            "exchange": exchange,
            "mode": "tick",
            "tick_type": tick_type,
        }

    def unregister(self, req_id: int) -> None:
        self._req_info.pop(req_id, None)
        self._snapshot_state.pop(req_id, None)

    def tick_price(
        self,
        req_id: int,
        tick_type: int,
        price: float,
        attrib: Any,
    ) -> None:
        info = self._req_info.get(req_id)
        if not info:
            return
        field = _tick_type_to_field(tick_type)
        if field and info.get("mode") == "snapshot":
            state = self._snapshot_state.setdefault(req_id, {})
            state[field] = price

    def tick_size(
        self,
        req_id: int,
        tick_type: int,
        size: Decimal,
    ) -> None:
        info = self._req_info.get(req_id)
        if not info:
            return
        field = _tick_type_to_field(tick_type)
        if field and info.get("mode") == "snapshot":
            state = self._snapshot_state.setdefault(req_id, {})
            state[field] = _decimal_to_int(size)

    def tick_snapshot_end(self, req_id: int) -> None:
        info = self._req_info.get(req_id)
        if not info or info.get("mode") != "snapshot":
            return
        state = self._snapshot_state.get(req_id, {})
        snapshot = QuoteSnapshot(
            req_id=req_id,
            symbol=info["symbol"],
            sec_type=info["sec_type"],
            exchange=info["exchange"],
            bid=state.get("bid"),
            ask=state.get("ask"),
            last=state.get("last"),
            bid_size=state.get("bid_size"),
            ask_size=state.get("ask_size"),
            last_size=state.get("last_size"),
            volume=state.get("volume"),
            snapshot_time_utc=datetime.now(timezone.utc),
        )
        try:
            self._repository.insert_snapshot(snapshot)
        except Exception as e:
            logger.exception("insert_snapshot failed for req_id=%s: %s", req_id, e)
        self.unregister(req_id)

    def tick_by_tick_all_last(
        self,
        req_id: int,
        tick_type: int,
        time_int: int,
        price: float,
        size: Decimal,
        tick_attrib_last: TickAttribLast,
        exchange: str,
        special_conditions: str,
    ) -> None:
        info = self._req_info.get(req_id)
        if not info:
            return
        t = _time_int_to_utc(time_int)
        tick_type_str = "AllLast" if tick_type == 1 else "Last"
        record = TickRecord(
            req_id=req_id,
            symbol=info["symbol"],
            sec_type=info["sec_type"],
            exchange=info["exchange"],
            tick_type=tick_type_str,
            time_utc=t,
            price=price,
            size=_decimal_to_int(size),
            bid_price=None,
            ask_price=None,
            bid_size=None,
            ask_size=None,
        )
        try:
            self._repository.insert_ticks([record])
        except Exception as e:
            logger.exception("insert_ticks failed for req_id=%s: %s", req_id, e)

    def tick_by_tick_bid_ask(
        self,
        req_id: int,
        time_int: int,
        bid_price: float,
        ask_price: float,
        bid_size: Decimal,
        ask_size: Decimal,
        tick_attrib_bid_ask: TickAttribBidAsk,
    ) -> None:
        info = self._req_info.get(req_id)
        if not info:
            return
        t = _time_int_to_utc(time_int)
        record = TickRecord(
            req_id=req_id,
            symbol=info["symbol"],
            sec_type=info["sec_type"],
            exchange=info["exchange"],
            tick_type="BidAsk",
            time_utc=t,
            price=None,
            size=None,
            bid_price=bid_price,
            ask_price=ask_price,
            bid_size=_decimal_to_int(bid_size),
            ask_size=_decimal_to_int(ask_size),
        )
        try:
            self._repository.insert_ticks([record])
        except Exception as e:
            logger.exception("insert_ticks failed for req_id=%s: %s", req_id, e)

    def tick_by_tick_mid_point(self, req_id: int, time_int: int, mid_point: float) -> None:
        info = self._req_info.get(req_id)
        if not info:
            return
        t = _time_int_to_utc(time_int)
        record = TickRecord(
            req_id=req_id,
            symbol=info["symbol"],
            sec_type=info["sec_type"],
            exchange=info["exchange"],
            tick_type="MidPoint",
            time_utc=t,
            price=mid_point,
            size=None,
            bid_price=None,
            ask_price=None,
            bid_size=None,
            ask_size=None,
        )
        try:
            self._repository.insert_ticks([record])
        except Exception as e:
            logger.exception("insert_ticks failed for req_id=%s: %s", req_id, e)


class IBMarketDataStreamClient(IMarketDataStreamClient):
    """Wraps EClient to implement IMarketDataStreamClient (reqMktData / reqTickByTickData / cancel)."""

    def __init__(
        self,
        client: Any,
        callback_handler: MarketDataCallbackHandler,
    ):
        self._client = client
        self._handler = callback_handler

    def request_snapshot(
        self,
        req_id: int,
        contract: Contract,
        regulatory_snapshot: bool = False,
    ) -> None:
        self._handler.register_snapshot_request(
            req_id,
            contract.symbol,
            contract.secType,
            contract.exchange or "",
        )
        self._client.reqMktData(
            req_id,
            contract,
            "",
            True,
            regulatory_snapshot,
            [],
        )

    def request_streaming_quotes(self, req_id: int, contract: Contract) -> None:
        self._handler.register_streaming_request(
            req_id,
            contract.symbol,
            contract.secType,
            contract.exchange or "",
        )
        self._client.reqMktData(
            req_id,
            contract,
            "",
            False,
            False,
            [],
        )

    def request_tick_by_tick(
        self,
        req_id: int,
        contract: Contract,
        tick_type: str = "Last",
        number_of_ticks: int = 0,
        ignore_size: bool = False,
    ) -> None:
        if tick_type not in ("Last", "AllLast", "BidAsk", "MidPoint"):
            raise ValueError(f"tick_type must be Last, AllLast, BidAsk, or MidPoint; got {tick_type}")
        self._handler.register_tick_by_tick_request(
            req_id,
            contract.symbol,
            contract.secType,
            contract.exchange or "",
            tick_type,
        )
        self._client.reqTickByTickData(
            req_id,
            contract,
            tick_type,
            number_of_ticks,
            ignore_size,
        )

    def cancel_mkt_data(self, req_id: int) -> None:
        self._client.cancelMktData(req_id)
        self._handler.unregister(req_id)

    def cancel_tick_by_tick(self, req_id: int) -> None:
        self._client.cancelTickByTickData(req_id)
        self._handler.unregister(req_id)


def next_streaming_req_id() -> int:
    """Return a new request ID for streaming/tick requests (caller manages uniqueness)."""
    if not hasattr(next_streaming_req_id, "_counter"):
        next_streaming_req_id._counter = _STREAMING_REQ_ID_BASE
    next_streaming_req_id._counter += 1
    if next_streaming_req_id._counter >= _STREAMING_REQ_ID_BASE + _MAX_REQ_IDS:
        raise RequestIdExhaustedError("Streaming request ID pool exhausted")
    return next_streaming_req_id._counter
