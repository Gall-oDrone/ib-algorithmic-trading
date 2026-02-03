# Interactive Brokers Algorithmic Trading Framework

A production-ready framework for algorithmic trading using Interactive Brokers API (IBAPI).

## Features

- **Object-Oriented Design**: Clean, modular architecture following SOLID principles
- **Connection Management**: Robust connection handling with automatic reconnection support
- **Order Management**: Comprehensive order placement and tracking
- **Historical Data**: Efficient historical data retrieval and storage
- **Account Management**: Account summary and P&L tracking with domain models
- **Portfolio Management**: Real-time position tracking
- **Technical Indicators**: Extensible indicator framework (ADX, ATR, Bollinger Bands, MACD, RSI, Stochastic)
- **AWS S3 Integration**: Production-ready S3 storage for historical data and DataFrames
- **Logging**: Comprehensive logging with configurable levels
- **Testing**: Full test suite with pytest including integration tests
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
├── conn/                   # Connection utilities
│   └── connection_mananger.py
├── handlers/               # Data handlers
│   ├── __init__.py
│   ├── contract_handler.py
│   └── historical_data_handler.py
├── order_management/       # Order management
│   ├── __init__.py
│   ├── order_manager.py
│   ├── order_builder.py
│   ├── orders.py
│   └── consts/
│       └── dataframes.py
├── account_and_portfolio/  # Account and portfolio
│   ├── __init__.py
│   ├── account.py          # Account domain model
│   ├── account_manager.py
│   ├── portfolio.py        # Portfolio domain model
│   └── portfolio_manager.py
├── storage/                # Data storage
│   ├── __init__.py
│   ├── dataframe.py
│   └── dataframe_manager.py
├── indicators/             # Technical indicators
│   ├── __init__.py
│   ├── base_indicator.py
│   ├── adx.py
│   ├── atr.py
│   ├── bollinger_bands.py
│   ├── macd.py
│   ├── rsi.py
│   └── stochastic.py
├── aws/                    # AWS S3 integration
│   ├── __init__.py
│   ├── README.md
│   ├── ETL_ARCHITECTURE.md
│   └── s3/
│       ├── __init__.py
│       ├── s3_client.py
│       ├── s3_manager.py
│       └── exceptions.py
├── consts/                 # Constants
│   ├── __init__.py
│   ├── contracts.py
│   ├── headers.py
│   └── orders.py
├── exceptions/             # Custom exceptions
│   ├── __init__.py
│   └── trading_exceptions.py
├── utils/                  # Utilities
│   ├── __init__.py
│   └── logger.py
├── scripts/
│   └── init.sh
├── archive/
│   └── eclient_and_ewrapper_class_intro.py
└── tests/                  # Test suite
    ├── __init__.py
    ├── conftest.py
    ├── fixtures/
    │   ├── __init__.py
    │   ├── contract_fixtures.py
    │   └── order_fixtures.py
    ├── adx/test_adx_indicator.py
    ├── atr/test_atr_indicator.py
    ├── bollinger_bands/test_bollinger_bands_indicator.py
    ├── consts/test_const_contracts.py, test_const_orders.py
    ├── core/test_connection_manager.py
    ├── handlers/test_contract_handler.py, test_historical_data_handler.py
    ├── integration/test_historical_data_integration.py, test_ndx_indicators_integration.py
    ├── macd/test_macd_indicator.py
    ├── order_management/test_order_manager.py, order_test.py
    ├── rsi/test_rsi_indicator.py
    ├── stochastic/test_stochastic_indicator.py
    └── storage/dataframe_test.py, test_s3_client.py, test_s3_manager.py
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

## AWS S3 Integration

The framework includes production-ready AWS S3 integration for storing historical data. See `aws/README.md` for detailed usage, configuration, and DataFrame upload/download operations.

## Key Classes

- **TradingApp**: Main application class integrating all components
- **ConnectionManager**: Manages IB API connection
- **ContractHandler**: Creates and validates IB contracts
- **OrderManager**: Manages order creation and tracking
- **HistoricalDataHandler**: Handles historical data storage
- **AccountManager** / **Account**: Manages account summary and P&L with domain model
- **PortfolioManager** / **Portfolio**: Tracks portfolio positions with domain model
- **Technical Indicators**: ADXIndicator, ATRIndicator, BollingerBandsIndicator, MACDIndicator, RSIIndicator, StochasticIndicator
- **S3Manager** / **Boto3S3Client**: AWS S3 storage for DataFrames and files

## Logging

Logs are written to the `logs/` directory by default. Configure logging levels in `config/settings.py` or via environment variables.

## License

This project is for educational purposes. Ensure compliance with Interactive Brokers API terms of service.

## Author

Diego Gallo

## Version

1.1.0
