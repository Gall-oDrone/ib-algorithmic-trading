# Interactive Brokers Algorithmic Trading Framework

A production-ready framework for algorithmic trading using Interactive Brokers API (IBAPI).

## Features

- **Object-Oriented Design**: Clean, modular architecture following SOLID principles
- **Connection Management**: Robust connection handling with automatic reconnection support
- **Order Management**: Comprehensive order placement and tracking
- **Historical Data**: Efficient historical data retrieval and storage
- **Account Management**: Account summary and P&L tracking
- **Portfolio Management**: Real-time position tracking
- **Technical Indicators**: Extensible indicator framework (MACD included)
- **Logging**: Comprehensive logging with configurable levels
- **Testing**: Full test suite with pytest
- **Configuration**: Environment-based configuration management

## Project Structure

```
courses/algorithmic_trading/
├── __init__.py
├── main.py                 # Main entry point
├── config/                 # Configuration management
│   ├── __init__.py
│   └── settings.py
├── core/                   # Core trading application
│   ├── __init__.py
│   ├── trading_app.py      # Main TradingApp class
│   └── connection_manager.py
├── handlers/               # Data handlers
│   ├── __init__.py
│   ├── contract_handler.py
│   └── historical_data_handler.py
├── order_management/       # Order management
│   ├── __init__.py
│   ├── order_manager.py
│   ├── order_builder.py
│   └── consts/
│       └── dataframes.py
├── account_and_portfolio/  # Account and portfolio
│   ├── __init__.py
│   ├── account_manager.py
│   └── portfolio_manager.py
├── storage/                # Data storage
│   ├── __init__.py
│   └── dataframe_manager.py
├── indicators/             # Technical indicators
│   ├── __init__.py
│   ├── base_indicator.py
│   └── macd.py
├── consts/                 # Constants
│   ├── __init__.py
│   ├── contracts.py
│   └── orders.py
├── exceptions/             # Custom exceptions
│   ├── __init__.py
│   └── trading_exceptions.py
├── utils/                  # Utilities
│   ├── __init__.py
│   └── logger.py
└── tests/                  # Test suite
    ├── __init__.py
    ├── conftest.py
    ├── test_contract_handler.py
    ├── test_order_manager.py
    ├── test_macd_indicator.py
    └── fixtures/
        ├── __init__.py
        ├── contract_fixtures.py
        └── order_fixtures.py
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure Interactive Brokers TWS or IB Gateway is running and configured:
   - Paper Trading: Port 7497 (TWS) or 4002 (Gateway)
   - Live Trading: Port 7496 (TWS) or 4001 (Gateway)

## Configuration

Configuration can be set via environment variables or defaults in `config/settings.py`:

- `IB_HOST`: Host address (default: 127.0.0.1)
- `IB_PORT`: Port number (default: 7497)
- `IB_CLIENT_ID`: Client ID (default: 1)
- `IB_DEBUG`: Enable debug mode (default: False)
- `IB_LOG_LEVEL`: Logging level (default: INFO)

## Usage

### Command Line Interface

```bash
# Request account summary
python -m algorithmic_trading.main --account-summary

# Request P&L for account
python -m algorithmic_trading.main --pnl DU111519

# Fetch historical data
python -m algorithmic_trading.main --fetch-data

# Place a limit order
python -m algorithmic_trading.main --place-limit-order

# Place a market order
python -m algorithmic_trading.main --place-market-order

# Enable debug mode
python -m algorithmic_trading.main --account-summary --debug
```

### Programmatic Usage

```python
from algorithmic_trading.core.trading_app import TradingApp
from algorithmic_trading.handlers.contract_handler import ContractHandler

# Create app
app = TradingApp()
app.connect()

# Create contract
contract_handler = ContractHandler()
contract = contract_handler.create_contract("AAPL")

# Request historical data
app.request_historical_data(1, contract, duration="1 D", bar_size="1 hour")

# Place order
app.place_limit_order(contract, "BUY", quantity=10, limit_price=150.0)

# Get account summary
app.request_account_summary(1, "All", "$LEDGER:ALL")
summary = app.get_account_summary()

# Disconnect
app.disconnect()
```

## Testing

Run tests with pytest:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_contract_handler.py

# Run with coverage
pytest --cov=algorithmic_trading tests/
```

## Key Classes

- **TradingApp**: Main application class integrating all components
- **ConnectionManager**: Manages IB API connection
- **ContractHandler**: Creates and validates IB contracts
- **OrderManager**: Manages order creation and tracking
- **HistoricalDataHandler**: Handles historical data storage
- **AccountManager**: Manages account summary and P&L
- **PortfolioManager**: Tracks portfolio positions
- **MACDIndicator**: MACD technical indicator implementation

## Logging

Logs are written to the `logs/` directory by default. Configure logging levels in `config/settings.py` or via environment variables.

## License

This project is for educational purposes. Ensure compliance with Interactive Brokers API terms of service.

## Author

Diego Gallo

## Version

1.0.0
