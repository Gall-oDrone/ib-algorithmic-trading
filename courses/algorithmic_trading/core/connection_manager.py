"""Connection management for IB API."""

import threading
import time
from typing import Optional

from ibapi.client import EClient
from ibapi.wrapper import EWrapper

from config import get_config
from exceptions import ConnectionError
from utils import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages connection to Interactive Brokers API."""
    
    def __init__(self, wrapper: EWrapper, client: EClient):
        """
        Initialize connection manager.
        
        Args:
            wrapper: EWrapper instance
            client: EClient instance
        """
        self.wrapper = wrapper
        self.client = client
        self.config = get_config()
        self.event = threading.Event()
        self._connected = False
        self._connection_thread: Optional[threading.Thread] = None
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to IB API."""
        return self._connected and self.client.isConnected()
    
    def connect(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        client_id: Optional[int] = None,
    ) -> None:
        """
        Connect to IB API.
        
        Args:
            host: Host address (defaults to config)
            port: Port number (defaults to config)
            client_id: Client ID (defaults to config)
            
        Raises:
            ConnectionError: If connection fails
        """
        host = host or self.config.host
        port = port or self.config.port
        client_id = client_id or self.config.client_id
        
        try:
            logger.info(f"Connecting to IB API at {host}:{port} with client ID {client_id}")
            # Call EClient.connect directly to avoid circular call if client overrides connect()
            EClient.connect(self.client, host, port, client_id)
            
            # Start websocket in a separate thread
            self._connection_thread = threading.Thread(
                target=self._run_websocket,
                daemon=True,
                name="IB_ConnectionThread"
            )
            self._connection_thread.start()
            
            # Wait for connection to establish
            time.sleep(self.config.connection_timeout)
            
            if self.client.isConnected():
                self._connected = True
                logger.info("Successfully connected to IB API")
            else:
                raise ConnectionError("Failed to establish connection to IB API")
                
        except Exception as e:
            self._connected = False
            logger.error(f"Connection error: {e}")
            raise ConnectionError(f"Failed to connect: {e}") from e
    
    def disconnect(self) -> None:
        """Disconnect from IB API."""
        if self.is_connected:
            logger.info("Disconnecting from IB API")
            self.event.set()
            EClient.disconnect(self.client)
            self._connected = False
            logger.info("Disconnected from IB API")
    
    def _run_websocket(self) -> None:
        """Run websocket in background thread."""
        try:
            self.client.run()
        except Exception as e:
            logger.error(f"Websocket error: {e}")
        finally:
            if self.event.is_set():
                EClient.disconnect(self.client)
