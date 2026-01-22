"""Configuration settings for the trading application."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Application configuration."""
    
    # Connection settings
    host: str = "127.0.0.1"
    paper_trading_gateway_port: int = 4002
    paper_trading_tws_port: int = 7497
    client_id: int = 1
    current_port: int = 7497
    
    # Timeout settings
    connection_timeout: int = 5
    default_timeout: int = 300  # 5 minutes
    
    # Logging
    debug: bool = False
    log_level: str = "INFO"
    
    # AWS S3 settings
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    aws_endpoint_url: Optional[str] = None
    aws_default_bucket: Optional[str] = None
    
    @property
    def port(self) -> int:
        """Get the current port."""
        return self.current_port
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            host=os.getenv("IB_HOST", "127.0.0.1"),
            paper_trading_gateway_port=int(os.getenv("IB_PAPER_GATEWAY_PORT", "4002")),
            paper_trading_tws_port=int(os.getenv("IB_PAPER_TWS_PORT", "7497")),
            client_id=int(os.getenv("IB_CLIENT_ID", "1")),
            current_port=int(os.getenv("IB_PORT", "7497")),
            connection_timeout=int(os.getenv("IB_CONNECTION_TIMEOUT", "5")),
            default_timeout=int(os.getenv("IB_DEFAULT_TIMEOUT", "300")),
            debug=os.getenv("IB_DEBUG", "False").lower() == "true",
            log_level=os.getenv("IB_LOG_LEVEL", "INFO"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            aws_endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
            aws_default_bucket=os.getenv("AWS_DEFAULT_BUCKET"),
        )


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
