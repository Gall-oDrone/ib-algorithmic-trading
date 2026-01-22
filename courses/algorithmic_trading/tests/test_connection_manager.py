"""Tests for ConnectionManager."""

import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from core.connection_manager import ConnectionManager
from exceptions import ConnectionError
from config import Config


@pytest.fixture
def mock_config():
    """Fixture for mock configuration."""
    config = MagicMock(spec=Config)
    config.host = "127.0.0.1"
    config.port = 7497
    config.client_id = 1
    config.connection_timeout = 0.1  # Very short timeout for tests
    return config


@pytest.fixture
def mock_wrapper():
    """Fixture for mock EWrapper."""
    return MagicMock()


@pytest.fixture
def mock_client():
    """Fixture for mock EClient."""
    client = MagicMock()
    client.isConnected.return_value = False
    return client


@pytest.fixture
def connection_manager(mock_wrapper, mock_client, mock_config):
    """Fixture for ConnectionManager with mocked dependencies."""
    with patch('core.connection_manager.get_config', return_value=mock_config):
        manager = ConnectionManager(mock_wrapper, mock_client)
    return manager


@pytest.fixture
def mock_eclient_connect():
    """Fixture to patch EClient.connect to prevent real connections."""
    with patch('core.connection_manager.EClient.connect') as mock_connect:
        yield mock_connect


class TestConnectionManagerInit:
    """Test class for ConnectionManager initialization."""

    def test_init_with_wrapper_and_client(self, mock_wrapper, mock_client, mock_config):
        """Test ConnectionManager initialization with wrapper and client."""
        with patch('core.connection_manager.get_config', return_value=mock_config):
            manager = ConnectionManager(mock_wrapper, mock_client)
        
        assert manager.wrapper == mock_wrapper
        assert manager.client == mock_client
        assert manager._connected is False
        assert manager._connection_thread is None
        assert isinstance(manager.event, threading.Event)
        
        print("\n=== ConnectionManager Initialization ===")
        print(f"Wrapper: {manager.wrapper}")
        print(f"Client: {manager.client}")
        print(f"Connected: {manager._connected}")
        print(f"Connection Thread: {manager._connection_thread}")

    def test_init_uses_config(self, mock_wrapper, mock_client, mock_config):
        """Test that ConnectionManager uses config values."""
        with patch('core.connection_manager.get_config', return_value=mock_config):
            manager = ConnectionManager(mock_wrapper, mock_client)
        
        assert manager.config == mock_config
        assert manager.config.host == "127.0.0.1"
        assert manager.config.port == 7497
        assert manager.config.client_id == 1


class TestConnectionManagerIsConnected:
    """Test class for is_connected property."""

    def test_is_connected_false_when_not_connected(self, connection_manager, mock_client):
        """Test is_connected returns False when not connected."""
        mock_client.isConnected.return_value = False
        connection_manager._connected = False
        
        assert connection_manager.is_connected is False

    def test_is_connected_false_when_internal_flag_false(self, connection_manager, mock_client):
        """Test is_connected returns False when _connected is False even if client says connected."""
        mock_client.isConnected.return_value = True
        connection_manager._connected = False
        
        assert connection_manager.is_connected is False

    def test_is_connected_false_when_client_disconnected(self, connection_manager, mock_client):
        """Test is_connected returns False when client is disconnected even if flag is True."""
        mock_client.isConnected.return_value = False
        connection_manager._connected = True
        
        assert connection_manager.is_connected is False

    def test_is_connected_true_when_fully_connected(self, connection_manager, mock_client):
        """Test is_connected returns True when both flag and client confirm connection."""
        mock_client.isConnected.return_value = True
        connection_manager._connected = True
        
        assert connection_manager.is_connected is True
        
        print("\n=== is_connected Property Tests ===")
        print(f"_connected: {connection_manager._connected}")
        print(f"client.isConnected(): {mock_client.isConnected()}")
        print(f"is_connected: {connection_manager.is_connected}")


class TestConnectionManagerConnect:
    """Test class for connect method."""

    def test_connect_uses_default_config_values(self, connection_manager, mock_client, mock_config, mock_eclient_connect):
        """Test connect uses config values when no parameters provided."""
        mock_client.isConnected.return_value = True
        
        connection_manager.connect()
        
        mock_eclient_connect.assert_called_once_with(
            mock_client,
            mock_config.host,
            mock_config.port,
            mock_config.client_id
        )
        
        print("\n=== Connect with Default Config ===")
        print(f"Host: {mock_config.host}")
        print(f"Port: {mock_config.port}")
        print(f"Client ID: {mock_config.client_id}")

    def test_connect_uses_provided_parameters(self, connection_manager, mock_client, mock_eclient_connect):
        """Test connect uses provided parameters over config values."""
        mock_client.isConnected.return_value = True
        
        connection_manager.connect(host="192.168.1.100", port=4001, client_id=5)
        
        mock_eclient_connect.assert_called_once_with(mock_client, "192.168.1.100", 4001, 5)
        
        print("\n=== Connect with Custom Parameters ===")
        print("Host: 192.168.1.100")
        print("Port: 4001")
        print("Client ID: 5")

    def test_connect_sets_connected_flag_on_success(self, connection_manager, mock_client, mock_eclient_connect):
        """Test connect sets _connected flag to True on successful connection."""
        mock_client.isConnected.return_value = True
        
        connection_manager.connect()
        
        assert connection_manager._connected is True

    def test_connect_starts_connection_thread(self, connection_manager, mock_client, mock_eclient_connect):
        """Test connect starts the connection thread."""
        mock_client.isConnected.return_value = True
        
        connection_manager.connect()
        
        assert connection_manager._connection_thread is not None
        assert connection_manager._connection_thread.daemon is True
        assert connection_manager._connection_thread.name == "IB_ConnectionThread"

    def test_connect_raises_connection_error_on_failure(self, connection_manager, mock_client, mock_eclient_connect):
        """Test connect raises ConnectionError when connection fails."""
        mock_client.isConnected.return_value = False
        
        with pytest.raises(ConnectionError, match="Failed to connect"):
            connection_manager.connect()
        
        assert connection_manager._connected is False
        
        print("\n=== Connect Failure Test ===")
        print("Expected: ConnectionError raised")
        print(f"_connected flag: {connection_manager._connected}")

    def test_connect_raises_connection_error_on_exception(self, connection_manager, mock_client, mock_eclient_connect):
        """Test connect raises ConnectionError when EClient.connect raises exception."""
        mock_eclient_connect.side_effect = Exception("Network error")
        
        with pytest.raises(ConnectionError, match="Failed to connect"):
            connection_manager.connect()
        
        assert connection_manager._connected is False

    def test_connect_partial_parameters(self, connection_manager, mock_client, mock_config, mock_eclient_connect):
        """Test connect with only some parameters provided."""
        mock_client.isConnected.return_value = True
        
        # Only provide host, use defaults for others
        connection_manager.connect(host="10.0.0.1")
        
        mock_eclient_connect.assert_called_once_with(
            mock_client,
            "10.0.0.1",
            mock_config.port,
            mock_config.client_id
        )


class TestConnectionManagerDisconnect:
    """Test class for disconnect method."""

    def test_disconnect_when_connected(self, connection_manager, mock_client):
        """Test disconnect calls client.disconnect when connected."""
        mock_client.isConnected.return_value = True
        connection_manager._connected = True
        
        connection_manager.disconnect()
        
        mock_client.disconnect.assert_called_once()
        assert connection_manager._connected is False
        assert connection_manager.event.is_set()
        
        print("\n=== Disconnect When Connected ===")
        print("client.disconnect() called: Yes")
        print(f"_connected flag: {connection_manager._connected}")
        print(f"event.is_set(): {connection_manager.event.is_set()}")

    def test_disconnect_when_not_connected(self, connection_manager, mock_client):
        """Test disconnect does nothing when not connected."""
        mock_client.isConnected.return_value = False
        connection_manager._connected = False
        
        connection_manager.disconnect()
        
        mock_client.disconnect.assert_not_called()
        
        print("\n=== Disconnect When Not Connected ===")
        print("client.disconnect() called: No (as expected)")

    def test_disconnect_sets_event(self, connection_manager, mock_client):
        """Test disconnect sets the event to signal thread shutdown."""
        mock_client.isConnected.return_value = True
        connection_manager._connected = True
        
        assert not connection_manager.event.is_set()
        
        connection_manager.disconnect()
        
        assert connection_manager.event.is_set()


class TestConnectionManagerRunWebsocket:
    """Test class for _run_websocket method."""

    def test_run_websocket_calls_client_run(self, connection_manager, mock_client):
        """Test _run_websocket calls client.run()."""
        connection_manager._run_websocket()
        
        mock_client.run.assert_called_once()

    def test_run_websocket_handles_exception(self, connection_manager, mock_client):
        """Test _run_websocket handles exceptions gracefully."""
        mock_client.run.side_effect = Exception("Websocket error")
        
        # Should not raise exception
        connection_manager._run_websocket()
        
        print("\n=== Run Websocket Exception Handling ===")
        print("Exception handled gracefully: Yes")

    def test_run_websocket_disconnects_when_event_set(self, connection_manager, mock_client):
        """Test _run_websocket disconnects client when event is set."""
        mock_client.run.side_effect = Exception("Test exception")
        connection_manager.event.set()
        
        connection_manager._run_websocket()
        
        mock_client.disconnect.assert_called_once()


class TestConnectionManagerIntegration:
    """Integration-style tests for ConnectionManager (still mocked but testing workflows)."""

    def test_connect_disconnect_workflow(self, connection_manager, mock_client, mock_eclient_connect):
        """Test full connect and disconnect workflow."""
        mock_client.isConnected.return_value = True
        
        # Initial state
        assert connection_manager.is_connected is False
        
        # Connect
        connection_manager.connect()
        assert connection_manager.is_connected is True
        assert connection_manager._connection_thread is not None
        
        # Disconnect
        connection_manager.disconnect()
        assert connection_manager._connected is False
        
        print("\n=== Connect/Disconnect Workflow ===")
        print("1. Initial state: Not connected")
        print("2. After connect(): Connected")
        print("3. After disconnect(): Not connected")

    def test_multiple_connect_attempts(self, connection_manager, mock_client, mock_eclient_connect):
        """Test handling of multiple connect attempts."""
        mock_client.isConnected.return_value = True
        
        # First connect
        connection_manager.connect()
        assert connection_manager._connected is True
        
        # Second connect (should work, replacing the connection)
        connection_manager.connect()
        assert connection_manager._connected is True
        
        # Verify EClient.connect was called twice
        assert mock_eclient_connect.call_count == 2

    def test_disconnect_idempotent(self, connection_manager, mock_client):
        """Test that multiple disconnects are safe."""
        mock_client.isConnected.return_value = False
        connection_manager._connected = False
        
        # Multiple disconnects should not raise errors
        connection_manager.disconnect()
        connection_manager.disconnect()
        connection_manager.disconnect()
        
        # disconnect should never be called since we're not connected
        mock_client.disconnect.assert_not_called()
        
        print("\n=== Idempotent Disconnect Test ===")
        print("Multiple disconnect() calls: Safe")


class TestConnectionManagerThreadSafety:
    """Test class for thread safety aspects."""

    def test_event_initially_not_set(self, connection_manager):
        """Test that event is not set initially."""
        assert not connection_manager.event.is_set()

    def test_event_can_be_used_for_signaling(self, connection_manager):
        """Test that event can be used for thread signaling."""
        # Clear state
        connection_manager.event.clear()
        assert not connection_manager.event.is_set()
        
        # Set event
        connection_manager.event.set()
        assert connection_manager.event.is_set()
        
        # Clear again
        connection_manager.event.clear()
        assert not connection_manager.event.is_set()

    def test_connection_thread_is_daemon(self, connection_manager, mock_client, mock_eclient_connect):
        """Test that connection thread is a daemon thread."""
        mock_client.isConnected.return_value = True
        
        connection_manager.connect()
        
        assert connection_manager._connection_thread.daemon is True
        
        print("\n=== Daemon Thread Test ===")
        print(f"Thread daemon: {connection_manager._connection_thread.daemon}")
        print("This ensures thread won't prevent program exit")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
