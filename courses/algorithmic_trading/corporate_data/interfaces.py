"""Abstract interfaces for corporate WSH data requests and persistence."""

from abc import ABC, abstractmethod

from corporate_data.models import WshEventRecord


class ICorporateDataRepository(ABC):
    """Abstract repository for persisting WSH corporate event records."""

    @abstractmethod
    def insert_event(self, event: WshEventRecord) -> None:
        """Insert a single corporate event record."""
        pass


class ICorporateDataClient(ABC):
    """Abstract interface for requesting/canceling IB WSH corporate events."""

    @abstractmethod
    def request_wsh_event_data(
        self,
        req_id: int,
        contract: object,
        filter_payload: dict,
    ) -> None:
        """Request WSH event data using reqWshEventData."""
        pass

    @abstractmethod
    def cancel_wsh_event_data(self, req_id: int) -> None:
        """Cancel reqWshEventData request for req_id."""
        pass

    @abstractmethod
    def request_wsh_event_data_batch(
        self,
        requests: list,
    ) -> None:
        """Submit multiple reqWshEventData requests without waiting in between."""
        pass
