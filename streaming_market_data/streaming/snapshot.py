"""Snapshot-only market data (reqMktData with snapshot=True or regulatory snapshot)."""

from ibapi.contract import Contract

from streaming_market_data.interfaces import IMarketDataStreamClient


class SnapshotRequester:
    """Requests a single L1 snapshot for a contract and persists via repository (via callback handler)."""

    def __init__(self, client: IMarketDataStreamClient):
        self._client = client

    def request(
        self,
        req_id: int,
        contract: Contract,
        regulatory_snapshot: bool = False,
    ) -> None:
        """Request one snapshot; handler will persist on tickSnapshotEnd."""
        self._client.request_snapshot(req_id, contract, regulatory_snapshot)

    def cancel(self, req_id: int) -> None:
        """Cancel snapshot subscription (e.g. if still waiting)."""
        self._client.cancel_mkt_data(req_id)
