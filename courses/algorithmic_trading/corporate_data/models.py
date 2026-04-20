"""Immutable value objects for IBKR WSH corporate events."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class WshEventRecord:
    """Captured and transformed corporate event payload from reqWshEventData."""

    req_id: int
    symbol: str
    sec_type: str
    exchange: str
    filter_payload: Dict[str, Any]
    raw_json: str
    json_payload: Dict[str, Any]
    yaml_payload: str
    received_at_utc: datetime

    def __post_init__(self) -> None:
        if not self.raw_json.strip():
            raise ValueError("raw_json must be a non-empty JSON string")
        if not isinstance(self.json_payload, dict):
            raise ValueError("json_payload must be a dictionary")
        if self.received_at_utc.tzinfo is None:
            object.__setattr__(
                self,
                "received_at_utc",
                self.received_at_utc.replace(tzinfo=timezone.utc),
            )
