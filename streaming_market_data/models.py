"""Immutable value objects for ticks and snapshots (aligned with IBAPI callbacks)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class TickRecord:
    """A single tick (Last, BidAsk, or MidPoint) from tick-by-tick or L1 stream."""

    req_id: int
    symbol: str
    sec_type: str
    exchange: str
    tick_type: str  # "Last", "AllLast", "BidAsk", "MidPoint"
    time_utc: datetime
    price: Optional[float] = None
    size: Optional[int] = None
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None

    def __post_init__(self) -> None:
        if self.tick_type not in ("Last", "AllLast", "BidAsk", "MidPoint"):
            raise ValueError(
                f"tick_type must be one of Last, AllLast, BidAsk, MidPoint; got {self.tick_type}"
            )


@dataclass(frozen=True)
class QuoteSnapshot:
    """Top-of-book snapshot from reqMktData(snapshot=True) or regulatory snapshot."""

    req_id: int
    symbol: str
    sec_type: str
    exchange: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    last_size: Optional[int] = None
    volume: Optional[int] = None
    snapshot_time_utc: Optional[datetime] = None
