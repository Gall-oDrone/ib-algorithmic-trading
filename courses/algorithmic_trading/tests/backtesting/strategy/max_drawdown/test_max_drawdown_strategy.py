"""Tests for Maximum Drawdown backtesting strategy.

Integration tests require TWS/Gateway running with paper account and API enabled.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

parent_dir = Path(__file__).parent.parent.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from backtesting.strategy.base_strategy import BaseBacktestStrategy
from backtesting.strategy.max_drawdown import (
    MaxDrawdownStrategy,
    calculate_max_drawdown,
)
from tests.backtesting.chart_utils import save_backtest_metrics_charts


@pytest.fixture
def sample_equity_series():
    """Sample equity curve (1 year of daily data)."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=365, freq="D")
    equity = 100 * (1 + np.cumsum(np.random.randn(365) * 0.005) / 10)
    equity = np.maximum(equity, 1.0)
    return pd.Series(equity, index=dates)


@pytest.fixture
def constant_equity():
    """Constant equity -> zero drawdown."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    return pd.Series(100.0, index=dates)


@pytest.fixture
def equity_with_known_drawdown():
    """Equity that peaks at 100, drops to 80, recovers to 90 -> 20% max drawdown."""
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    equity = pd.Series([100.0, 105.0, 80.0, 85.0, 90.0], index=dates)
    return equity


@pytest.fixture
def multi_year_equity():
    """~3 years of daily equity for multi-period metrics."""
    dates = pd.date_range("2022-01-01", periods=365 * 3 + 1, freq="D")
    t = np.arange(len(dates)) / (365.25 * 3)
    equity = 100 * (1.10 ** (t * 3))
    return pd.Series(equity, index=dates)


def test_calculate_max_drawdown_function(sample_equity_series):
    """Test convenience function returns expected keys."""
    result = calculate_max_drawdown(sample_equity_series)
    assert "max_drawdown_1y" in result
    assert "max_drawdown_full" in result
    assert isinstance(result["max_drawdown_1y"], (float, np.floating))
    assert result["max_drawdown_full"] >= 0


def test_max_drawdown_strategy_class(sample_equity_series):
    """Test strategy returns max drawdown for default periods."""
    strategy = MaxDrawdownStrategy(
        time_periods=[1, 3],
        include_full_period=True,
        include_rolling=False,
    )
    result = strategy.evaluate(sample_equity_series)
    assert "max_drawdown_1y" in result
    assert "max_drawdown_3y" in result
    assert "max_drawdown_full" in result


def test_max_drawdown_custom_time_periods(sample_equity_series):
    """Test custom time_periods."""
    strategy = MaxDrawdownStrategy(time_periods=[1, 2], include_full_period=True)
    result = strategy.evaluate(sample_equity_series)
    assert "max_drawdown_1y" in result
    assert "max_drawdown_2y" in result
    assert "max_drawdown_3y" not in result
    assert "max_drawdown_full" in result


def test_max_drawdown_insufficient_data():
    """Test with single point returns NaN."""
    equity = pd.Series([100.0], index=pd.DatetimeIndex(["2024-01-01"]))
    result = calculate_max_drawdown(equity)
    assert "max_drawdown_1y" in result
    assert "max_drawdown_full" in result
    assert np.isnan(result["max_drawdown_1y"])
    assert np.isnan(result["max_drawdown_full"])


def test_max_drawdown_constant_equity(constant_equity):
    """Test constant equity yields zero drawdown."""
    result = calculate_max_drawdown(constant_equity)
    assert result["max_drawdown_full"] == 0.0


def test_max_drawdown_known_drawdown(equity_with_known_drawdown):
    """Test equity that drops 100->80 gives 20% max drawdown."""
    result = calculate_max_drawdown(equity_with_known_drawdown)
    # Peak 105, trough 80 -> (105-80)/105 ≈ 0.238
    assert "max_drawdown_full" in result
    assert abs(result["max_drawdown_full"] - (105.0 - 80.0) / 105.0) < 1e-6


def test_max_drawdown_evaluate_from_dataframe(sample_equity_series):
    """Test evaluate_from_dataframe with OHLC-style DataFrame."""
    df = sample_equity_series.to_frame("Close")
    strategy = MaxDrawdownStrategy(time_periods=[1], include_full_period=True)
    result = strategy.evaluate_from_dataframe(df, value_col="Close")
    assert "max_drawdown_1y" in result
    assert "max_drawdown_full" in result


def test_max_drawdown_evaluate_from_dataframe_with_date_col():
    """Test evaluate_from_dataframe with explicit date column."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    equity = 100 * (1 + np.cumsum(np.random.randn(100) * 0.01))
    df = pd.DataFrame({"date": dates, "Close": equity})
    strategy = MaxDrawdownStrategy(time_periods=[1], include_full_period=True)
    result = strategy.evaluate_from_dataframe(df, value_col="Close", date_col="date")
    assert "max_drawdown_full" in result


def test_max_drawdown_include_rolling(sample_equity_series):
    """Test include_rolling adds rolling series."""
    result = calculate_max_drawdown(
        sample_equity_series,
        time_periods=[1],
        include_full_period=True,
        include_rolling=True,
    )
    assert "rolling_max_drawdown_1y" in result
    assert isinstance(result["rolling_max_drawdown_1y"], pd.Series)
    assert len(result["rolling_max_drawdown_1y"]) == len(sample_equity_series)


def test_max_drawdown_no_full_period(sample_equity_series):
    """Test include_full_period=False omits max_drawdown_full."""
    strategy = MaxDrawdownStrategy(
        time_periods=[1],
        include_full_period=False,
    )
    result = strategy.evaluate(sample_equity_series)
    assert "max_drawdown_full" not in result
    assert "max_drawdown_1y" in result


def test_max_drawdown_invalid_time_periods():
    """Test invalid time_periods raise."""
    with pytest.raises(ValueError, match="positive"):
        MaxDrawdownStrategy(time_periods=[0])
    with pytest.raises(ValueError, match="at least one"):
        MaxDrawdownStrategy(time_periods=[])


def test_max_drawdown_inherits_base():
    """Test MaxDrawdownStrategy is a BaseBacktestStrategy."""
    strategy = MaxDrawdownStrategy(time_periods=[1])
    assert isinstance(strategy, BaseBacktestStrategy)
    assert strategy.name == "MaxDrawdown"


def test_max_drawdown_ndx_real_data():
    """
    Integration test: Max Drawdown on NDX daily data from TWS.
    Merges CAGAR + Volatility/Sharpe + MaxDrawdown into one CSV.
    """
    try:
        import time
        import threading
        from datetime import datetime
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
        from ibapi.common import BarData
        from handlers.historical_data_handler import HistoricalDataHandler
        from handlers.contract_handler import ContractHandler
        from config import get_config
        from backtesting.strategy.cagar import CAGARStrategy
        from backtesting.strategy.volatility_sharpe import VolatilitySharpeStrategy
    except ImportError as e:
        pytest.skip(f"Required modules not available: {e}")

    class NDXTestApp(EWrapper, EClient):
        def __init__(self):
            EClient.__init__(self, self)
            self.data_handler = HistoricalDataHandler()
            self.contract_handler = ContractHandler()
            self.connected = False
            self.data_received = False

        def nextValidId(self, orderId):
            self.connected = True

        def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
            if errorCode not in [2104, 2106, 2158]:
                print(f"   Error {reqId} {errorCode}: {errorString}")

        def historicalData(self, reqId, bar: BarData):
            self.data_handler.add_bar(reqId, bar)

        def historicalDataEnd(self, reqId, start, end):
            self.data_received = True
            print(f"   Historical data complete for NDX: {start} to {end}")

    config = get_config()
    app = NDXTestApp()
    try:
        app.connect(config.host, config.port, clientId=210)
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()
        time.sleep(3)
        if not app.isConnected():
            pytest.skip("Could not connect to IB TWS. Skipping integration test.")
    except Exception as e:
        pytest.skip(f"Could not connect to IB TWS: {e}")

    try:
        print("\n[1/4] Requesting NDX historical data (3Y daily)...")
        contract = app.contract_handler.create_contract(
            "NDX", sec_type="IND", currency="USD", exchange="NASDAQ"
        )
        app.data_handler.register_request(0, "NDX")
        app.reqHistoricalData(
            reqId=0,
            contract=contract,
            endDateTime="",
            durationStr="3 Y",
            barSizeSetting="1 day",
            whatToShow="ADJUSTED_LAST",
            useRTH=1,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[],
        )

        print("\n[2/4] Waiting for data...")
        max_wait = 30
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if app.data_received:
                break
            time.sleep(1)
        if not app.data_received:
            pytest.skip("No data received from IB TWS. Skipping integration test.")

        print("\n[3/4] Computing CAGAR + Volatility/Sharpe + MaxDrawdown on NDX...")
        data = app.data_handler.get_data(0)
        if not data:
            pytest.skip("No data available. Skipping integration test.")
        df = pd.DataFrame(data)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
        close = df["Close"].dropna()
        if len(close) < 2:
            pytest.skip("Insufficient NDX data.")

        cagar_strategy = CAGARStrategy(
            time_periods=[1, 3],
            include_full_period=True,
            include_rolling=False,
        )
        vol_sharpe_strategy = VolatilitySharpeStrategy(
            time_periods=[1, 3],
            include_full_period=True,
            include_rolling=False,
            risk_free_rate_annual=0.0,
        )
        max_dd_strategy = MaxDrawdownStrategy(
            time_periods=[1, 3],
            include_full_period=True,
            include_rolling=False,
        )
        cagar_result = cagar_strategy.evaluate(close)
        vol_sharpe_result = vol_sharpe_strategy.evaluate(close)
        max_dd_result = max_dd_strategy.evaluate(close)

        def scalar_metrics(d):
            return {
                k: v
                for k, v in d.items()
                if isinstance(v, (int, float, np.floating))
            }

        merged = {
            **scalar_metrics(cagar_result),
            **scalar_metrics(vol_sharpe_result),
            **scalar_metrics(max_dd_result),
        }

        current_date = datetime.now().strftime("%Y%m%d")
        data_root = Path(__file__).parent.parent.parent.parent.parent / "data" / "backtesting"

        # All metrics (combined CSV + chart) -> all_metrics/
        base_all = data_root / "all_metrics" / "ndx" / current_date
        base_all.mkdir(parents=True, exist_ok=True)
        out_path_all = base_all / f"ndx_backtest_metrics_{current_date}.csv"
        pd.DataFrame([merged]).to_csv(out_path_all, index=False)
        print(f"   Exported (all metrics) to: {out_path_all}")
        save_backtest_metrics_charts(merged, base_all, label="daily", date_str=current_date)

        # Individual max_drawdown result + chart -> max_drawdown/
        base_md = data_root / "max_drawdown" / "ndx" / current_date
        base_md.mkdir(parents=True, exist_ok=True)
        out_path_md = base_md / f"ndx_max_drawdown_{current_date}.csv"
        pd.DataFrame([scalar_metrics(max_dd_result)]).to_csv(out_path_md, index=False)
        print(f"   Exported (max_drawdown) to: {out_path_md}")
        save_backtest_metrics_charts(max_dd_result, base_md, label="daily", date_str=current_date)

        assert out_path_all.exists()
        assert out_path_md.exists()
        assert "max_drawdown_full" in merged
        assert "cagar_1y" in merged and "volatility_1y" in merged and "sharpe_full" in merged
        print(
            f"\nMax Drawdown full: {merged.get('max_drawdown_full')}, "
            f"CAGAR 1Y: {merged.get('cagar_1y')}, Vol 1Y: {merged.get('volatility_1y')}"
        )
    finally:
        app.disconnect()


INTRADAY_BAR_SIZES = [
    ("5 mins", "5min"),
    ("15 mins", "15min"),
    ("1 hour", "1hour"),
]


@pytest.mark.parametrize("bar_size,bar_size_label", INTRADAY_BAR_SIZES)
def test_max_drawdown_ndx_intraday_real_data(bar_size, bar_size_label):
    """
    Integration test: Max Drawdown on NDX intraday data from TWS.
    Writes combined CAGAR + Volatility/Sharpe + MaxDrawdown to CSV.
    """
    try:
        import time
        import threading
        from datetime import datetime
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
        from ibapi.common import BarData
        from handlers.historical_data_handler import HistoricalDataHandler
        from handlers.contract_handler import ContractHandler
        from config import get_config
        from backtesting.strategy.cagar import CAGARStrategy
        from backtesting.strategy.volatility_sharpe import VolatilitySharpeStrategy
    except ImportError as e:
        pytest.skip(f"Required modules not available: {e}")

    class NDXIntradayTestApp(EWrapper, EClient):
        def __init__(self):
            EClient.__init__(self, self)
            self.data_handler = HistoricalDataHandler()
            self.contract_handler = ContractHandler()
            self.connected = False
            self.data_received = False

        def nextValidId(self, orderId):
            self.connected = True

        def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
            if errorCode not in [2104, 2106, 2158]:
                print(f"   Error {reqId} {errorCode}: {errorString}")

        def historicalData(self, reqId, bar: BarData):
            self.data_handler.add_bar(reqId, bar)

        def historicalDataEnd(self, reqId, start, end):
            self.data_received = True
            print(
                f"   Historical data complete for NDX ({bar_size_label}): {start} to {end}"
            )

    config = get_config()
    app = NDXIntradayTestApp()
    try:
        app.connect(config.host, config.port, clientId=211)
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()
        time.sleep(3)
        if not app.isConnected():
            pytest.skip("Could not connect to IB TWS. Skipping integration test.")
    except Exception as e:
        pytest.skip(f"Could not connect to IB TWS: {e}")

    try:
        print(f"\n[1/4] Requesting NDX intraday data ({bar_size_label})...")
        contract = app.contract_handler.create_contract(
            "NDX", sec_type="IND", currency="USD", exchange="NASDAQ"
        )
        app.data_handler.register_request(0, f"NDX_{bar_size_label}")
        app.reqHistoricalData(
            reqId=0,
            contract=contract,
            endDateTime="",
            durationStr="1 W",
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=1,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[],
        )

        print("\n[2/4] Waiting for data...")
        max_wait = 30
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if app.data_received:
                break
            time.sleep(1)
        if not app.data_received:
            pytest.skip(
                f"No data received from IB TWS for {bar_size_label}. Skipping."
            )

        print("\n[3/4] Computing CAGAR + Volatility/Sharpe + MaxDrawdown on NDX intraday...")
        data = app.data_handler.get_data(0)
        if not data:
            pytest.skip(f"No data for {bar_size_label}.")
        df = pd.DataFrame(data)
        if "Date" in df.columns:
            try:
                df["Date"] = pd.to_datetime(
                    df["Date"], format="%Y%m%d %H:%M:%S %Z"
                )
            except Exception:
                try:
                    df["Date"] = pd.to_datetime(
                        df["Date"], format="%Y%m%d %H:%M:%S"
                    )
                except Exception:
                    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df.set_index("Date", inplace=True)
        close = df["Close"].dropna()
        if len(close) < 2:
            pytest.skip(
                f"Insufficient NDX intraday data ({bar_size_label})."
            )

        cagar_strategy = CAGARStrategy(
            time_periods=[1],
            include_full_period=True,
            include_rolling=False,
        )
        vol_sharpe_strategy = VolatilitySharpeStrategy(
            time_periods=[1],
            include_full_period=True,
            include_rolling=False,
            risk_free_rate_annual=0.0,
        )
        max_dd_strategy = MaxDrawdownStrategy(
            time_periods=[1],
            include_full_period=True,
            include_rolling=False,
        )
        cagar_result = cagar_strategy.evaluate(close)
        vol_sharpe_result = vol_sharpe_strategy.evaluate(close)
        max_dd_result = max_dd_strategy.evaluate(close)

        def scalar_metrics(d):
            return {
                k: v
                for k, v in d.items()
                if isinstance(v, (int, float, np.floating))
            }

        merged = {
            **scalar_metrics(cagar_result),
            **scalar_metrics(vol_sharpe_result),
            **scalar_metrics(max_dd_result),
        }

        current_date = datetime.now().strftime("%Y%m%d")
        data_root = Path(__file__).parent.parent.parent.parent.parent / "data" / "backtesting"

        # All metrics (combined) -> all_metrics/ndx/<date>/intraday/<tf>/
        base_all = data_root / "all_metrics" / "ndx" / current_date / "intraday" / bar_size_label
        base_all.mkdir(parents=True, exist_ok=True)
        out_path_all = base_all / f"ndx_backtest_metrics_intraday_{bar_size_label}_{current_date}.csv"
        pd.DataFrame([merged]).to_csv(out_path_all, index=False)
        print(f"   Exported (all metrics) to: {out_path_all}")
        save_backtest_metrics_charts(merged, base_all, label=bar_size_label, date_str=current_date)

        # Individual max_drawdown -> max_drawdown/ndx/<date>/intraday/<tf>/
        base_md = data_root / "max_drawdown" / "ndx" / current_date / "intraday" / bar_size_label
        base_md.mkdir(parents=True, exist_ok=True)
        out_path_md = base_md / f"ndx_max_drawdown_intraday_{bar_size_label}_{current_date}.csv"
        pd.DataFrame([scalar_metrics(max_dd_result)]).to_csv(out_path_md, index=False)
        print(f"   Exported (max_drawdown) to: {out_path_md}")
        save_backtest_metrics_charts(max_dd_result, base_md, label=bar_size_label, date_str=current_date)

        assert out_path_all.exists()
        assert out_path_md.exists()
        assert "max_drawdown_full" in merged
        assert "volatility_full" in merged and "sharpe_full" in merged
        print(
            f"\nMax Drawdown full ({bar_size_label}): {merged.get('max_drawdown_full')}, "
            f"Volatility full: {merged.get('volatility_full')}, Sharpe full: {merged.get('sharpe_full')}"
        )
    finally:
        app.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
