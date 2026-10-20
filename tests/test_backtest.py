"""Tests for the Quantitative Backtesting Engine."""
import pytest
from src.trading.backtest import run_backtest

def test_run_backtest_with_mock_data():
    # Generate 100 oscillating candles around 100.0 with 2% wave
    import math
    candles = []
    base_price = 100.0
    for i in range(120):
        wave = math.sin(i / 5.0) * 3.0
        p = base_price + wave
        candles.append({
            "open_time": i,
            "open": p * 0.999,
            "high": p * 1.01,
            "low": p * 0.99,
            "close": p,
            "volume": 50.0
        })

    res = run_backtest(candles, initial_capital=100.0, step_percent=1.0)
    assert "final_equity" in res
    assert "total_profit_usd" in res
    assert "win_rate_percent" in res
    assert res["initial_capital"] == 100.0
    assert res["final_equity"] >= 0.0
    assert res["max_drawdown_percent"] >= 0.0
