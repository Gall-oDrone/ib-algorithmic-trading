"""Immutable value objects for IB fundamental reports."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class FundamentalReportRecord:
    """Captured and transformed fundamental report from reqFundamentalData."""

    req_id: int
    symbol: str
    sec_type: str
    exchange: str
    report_type: str
    xml_payload: str
    json_payload: Dict[str, Any]
    yaml_payload: str
    received_at_utc: datetime

    def __post_init__(self) -> None:
        if not self.xml_payload.strip():
            raise ValueError("xml_payload must be a non-empty XML string")
        if not isinstance(self.json_payload, dict):
            raise ValueError("json_payload must be a dictionary")
        if self.received_at_utc.tzinfo is None:
            object.__setattr__(
                self,
                "received_at_utc",
                self.received_at_utc.replace(tzinfo=timezone.utc),
            )
