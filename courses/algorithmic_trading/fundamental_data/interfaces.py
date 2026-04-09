"""Abstract interfaces for fundamental data requests and persistence."""

from abc import ABC, abstractmethod

from fundamental_data.models import FundamentalReportRecord


class IFundamentalDataRepository(ABC):
    """Abstract repository for persisting fundamental reports."""

    @abstractmethod
    def insert_report(self, report: FundamentalReportRecord) -> None:
        """Insert a single fundamental report record."""
        pass


class IFundamentalDataClient(ABC):
    """Abstract interface for requesting/canceling IB fundamental data."""

    @abstractmethod
    def request_fundamental_data(
        self,
        req_id: int,
        contract: object,
        report_type: str,
    ) -> None:
        """Request fundamental data with reqFundamentalData."""
        pass

    @abstractmethod
    def cancel_fundamental_data(self, req_id: int) -> None:
        """Cancel reqFundamentalData request for req_id."""
        pass
