"""Main entry point for the trading application."""

import argparse
import time
import sys

import sys
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from core.trading_app import TradingApp
from config import get_config
from utils import setup_logger
from handlers.contract_handler import ContractHandler
from tests.fixtures import (
    get_test_contract_apple,
    get_test_contract_google,
    get_test_contract_palantir,
    get_test_contract_facebook,
    get_buy_limit_order_test1,
    get_buy_market_order_test1,
    get_buy_stop_order_test1,
    get_buy_trail_stop_order_test1,
)
from run_ndx_intraday import run_ndx_intraday_loop


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Interactive Brokers Algorithmic Trading Application"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="IB API host (default: from config)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="IB API port (default: from config)",
    )
    parser.add_argument(
        "--client-id",
        type=int,
        default=None,
        help="Client ID (default: from config)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    parser.add_argument(
        "--fetch-data",
        action="store_true",
        help="Fetch historical data",
    )
    parser.add_argument(
        "--place-limit-order",
        action="store_true",
        help="Place a limit order",
    )
    parser.add_argument(
        "--place-market-order",
        action="store_true",
        help="Place a market order",
    )
    parser.add_argument(
        "--place-stop-order",
        action="store_true",
        help="Place a stop order",
    )
    parser.add_argument(
        "--place-trail-stop-order",
        action="store_true",
        help="Place a trailing stop order",
    )
    parser.add_argument(
        "--account-summary",
        action="store_true",
        help="Request account summary",
    )
    parser.add_argument(
        "--pnl",
        type=str,
        default=None,
        help="Request P&L for account",
    )
    parser.add_argument(
        "--ndx-intraday",
        action="store_true",
        help="Run NDX intraday strategy: fetch bars, run MACD+Stoch+ATR strategy, place/cancel orders on signal",
    )
    parser.add_argument(
        "--ndx-intraday-quantity",
        type=float,
        default=1.0,
        help="Order quantity for NDX intraday (default: 1.0)",
    )
    parser.add_argument(
        "--ndx-intraday-bar-size",
        type=str,
        default="5 mins",
        help="Bar size for NDX intraday (default: 5 mins)",
    )
    parser.add_argument(
        "--ndx-intraday-poll",
        type=int,
        default=300,
        help="Seconds between NDX intraday iterations (default: 300)",
    )
    return parser.parse_args()


def main():
    """Main application entry point."""
    args = parse_args()
    
    # Setup logging
    config = get_config()
    if args.debug:
        config.debug = True
    
    logger = setup_logger(level=config.log_level)
    logger.info("Starting Trading Application")
    
    # Create trading app
    app = TradingApp()
    app.debug = config.debug
    
    try:
        # Connect to IB API
        logger.info("Connecting to IB API...")
        app.connect(
            host=args.host,
            port=args.port,
            client_id=args.client_id,
        )
        
        # Wait for connection and next valid order ID
        time.sleep(5)
        
        # Request next valid order ID if not already received
        if app._next_valid_order_id is None:
            app.reqIds(-1)
            time.sleep(2)
        
        contract_handler = ContractHandler()
        start_time = time.time()
        timeout = config.default_timeout
        
        # Execute requested actions
        if args.fetch_data:
            logger.info("Fetching historical data...")
            app.fetch_stock_data(["AMZN", "TSLA", "NVDA"])
            time.sleep(10)  # Wait for data
            
            # Get dataframes
            dfs = app.get_historical_dataframes()
            for ticker, df in dfs.items():
                logger.info(f"DataFrame for {ticker}: {df.shape}")
        
        elif args.place_limit_order:
            logger.info("Placing limit order...")
            order = get_buy_limit_order_test1()
            contract_dict = get_test_contract_apple()
            contract = contract_handler.create_contract_from_dict(contract_dict)
            app.order_manager.set_order_details_from_dict(order)
            app.order_manager.create_order()
            app.place_order(contract, app.order_manager.order)
        
        elif args.place_market_order:
            logger.info("Placing market order...")
            order = get_buy_market_order_test1()
            contract_dict = get_test_contract_google()
            contract = contract_handler.create_contract_from_dict(contract_dict)
            app.order_manager.set_order_details_from_dict(order)
            app.order_manager.create_order()
            app.place_order(contract, app.order_manager.order)
        
        elif args.place_stop_order:
            logger.info("Placing stop order...")
            order = get_buy_stop_order_test1()
            contract_dict = get_test_contract_palantir()
            contract = contract_handler.create_contract_from_dict(contract_dict)
            app.order_manager.set_order_details_from_dict(order)
            app.order_manager.create_order()
            app.place_order(contract, app.order_manager.order)
        
        elif args.place_trail_stop_order:
            logger.info("Placing trailing stop order...")
            order = get_buy_trail_stop_order_test1()
            contract_dict = get_test_contract_facebook()
            contract = contract_handler.create_contract_from_dict(contract_dict)
            app.order_manager.set_order_details_from_dict(order)
            app.order_manager.create_order()
            app.place_order(contract, app.order_manager.order)
        
        elif args.account_summary:
            logger.info("Requesting account summary...")
            app.request_account_summary(-1, "All", "$LEDGER:ALL")
            time.sleep(2)
            summary = app.get_account_summary()
            logger.info(f"Account Summary:\n{summary}")
        
        elif args.pnl:
            logger.info(f"Requesting P&L for account {args.pnl}...")
            app.request_pnl(-1, args.pnl)
            time.sleep(2)
            pnl = app.get_pnl()
            logger.info(f"P&L:\n{pnl}")
        
        elif args.ndx_intraday:
            logger.info("Running NDX intraday strategy (connect, fetch bars, signals, place/cancel orders)...")
            run_ndx_intraday_loop(
                app,
                contract_handler,
                quantity=args.ndx_intraday_quantity,
                bar_size=args.ndx_intraday_bar_size,
                duration="1 W",
                poll_seconds=args.ndx_intraday_poll,
                timeout_seconds=timeout,
            )
        
        else:
            logger.info("No action specified. Use --help for available options.")
            logger.info("Example: python -m algorithmic_trading.main --account-summary")
        
        # Keep connection alive
        while time.time() - start_time < timeout:
            time.sleep(30)
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Disconnecting from IB API...")
        app.disconnect()
        logger.info("Application terminated")


if __name__ == "__main__":
    main()
