"""Tick-by-tick and optional L1 streaming market data."""

from ibapi.contract import Contract

from streaming_market_data.interfaces import IMarketDataStreamClient


class TickStreamRequester:
    """Requests tick-by-tick data (Last, AllLast, BidAsk, MidPoint) and optionally L1 streaming."""

    def __init__(self, client: IMarketDataStreamClient):
        self._client = client

    def request_tick_by_tick(
        self,
        req_id: int,
        contract: Contract,
        tick_type: str = "Last",
        number_of_ticks: int = 0,
        ignore_size: bool = False,
    ) -> None:
        """Start tick-by-tick stream; handler persists each tick to repository."""
        self._client.request_tick_by_tick(
            req_id,
            contract,
            tick_type=tick_type,
            number_of_ticks=number_of_ticks,
            ignore_size=ignore_size,
        )

    def cancel_tick_by_tick(self, req_id: int) -> None:
        """Stop tick-by-tick stream."""
        self._client.cancel_tick_by_tick(req_id)

    def request_streaming_quotes(self, req_id: int, contract: Contract) -> None:
        """Start L1 streaming quotes; handler can persist on change or periodically (configurable)."""
        self._client.request_streaming_quotes(req_id, contract)

    def cancel_streaming_quotes(self, req_id: int) -> None:
        """Stop L1 streaming."""
        self._client.cancel_mkt_data(req_id)
