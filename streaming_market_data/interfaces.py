"""Abstract interfaces for streaming client and market data repository."""

from abc import ABC, abstractmethod
from typing import List

from streaming_market_data.models import QuoteSnapshot, TickRecord  # noqa: I001


class IMarketDataRepository(ABC):
    """Abstract repository for persisting ticks and snapshots."""

    @abstractmethod
    def insert_ticks(self, ticks: List[TickRecord]) -> None:
        """Insert tick records (batch)."""
        pass

    @abstractmethod
    def insert_snapshot(self, snapshot: QuoteSnapshot) -> None:
        """Insert a single quote snapshot."""
        pass


class IMarketDataStreamClient(ABC):
    """Abstract interface for requesting/cancelling market data (IB client facade)."""

    @abstractmethod
    def request_snapshot(
        self,
        req_id: int,
        contract: object,
        regulatory_snapshot: bool = False,
    ) -> None:
        """Request a single L1 snapshot for the contract."""
        pass

    @abstractmethod
    def request_streaming_quotes(self, req_id: int, contract: object) -> None:
        """Request streaming L1 quotes for the contract."""
        pass

    @abstractmethod
    def request_tick_by_tick(
        self,
        req_id: int,
        contract: object,
        tick_type: str = "Last",
        number_of_ticks: int = 0,
        ignore_size: bool = False,
    ) -> None:
        """Request tick-by-tick data (Last, AllLast, BidAsk, MidPoint)."""
        pass

    @abstractmethod
    def cancel_mkt_data(self, req_id: int) -> None:
        """Cancel streaming/snapshot market data for req_id."""
        pass

    @abstractmethod
    def cancel_tick_by_tick(self, req_id: int) -> None:
        """Cancel tick-by-tick data for req_id."""
        pass
