"""Streaming market data configuration (env-based).

Requires Market Data API Acknowledgement and L1 subscription in IBKR Client Portal.
Tick-by-tick counts against IBKR market data line limits (e.g. 5 at 100 lines).
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class StreamingMarketDataConfig:
    """Configuration for streaming market data and PostgreSQL storage."""

    database_url: str
    max_streaming_symbols: int = 100
    snapshot_batch_interval_ms: int = 0
    use_regulatory_snapshot: bool = False

    @classmethod
    def from_env(cls) -> "StreamingMarketDataConfig":
        """Create configuration from environment variables."""
        url = (
            os.getenv("STREAMING_MARKET_DATA_DB_URL")
            or os.getenv("DATABASE_URL")
            or os.getenv("POSTGRES_URL")
            or "postgresql://localhost:5432/ib_streaming"
        )
        return cls(
            database_url=url,
            max_streaming_symbols=int(
                os.getenv("STREAMING_MARKET_DATA_MAX_SYMBOLS", "100")
            ),
            snapshot_batch_interval_ms=int(
                os.getenv("STREAMING_MARKET_DATA_SNAPSHOT_INTERVAL_MS", "0")
            ),
            use_regulatory_snapshot=os.getenv(
                "STREAMING_MARKET_DATA_USE_REGULATORY_SNAPSHOT", "false"
            ).lower()
            == "true",
        )


_config: Optional[StreamingMarketDataConfig] = None


def get_streaming_config() -> StreamingMarketDataConfig:
    """Get the global streaming market data config instance."""
    global _config
    if _config is None:
        _config = StreamingMarketDataConfig.from_env()
    return _config


def set_streaming_config(config: StreamingMarketDataConfig) -> None:
    """Set the global streaming market data config (e.g. for tests)."""
    global _config
    _config = config
