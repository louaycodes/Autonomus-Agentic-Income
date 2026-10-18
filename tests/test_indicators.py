import pytest
from src.trading.indicators import calculate_ema, calculate_rsi, evaluate_market_regime

def test_calculate_ema():
    prices = [10.0, 11.0, 12.0, 11.5, 13.0, 14.0, 13.5, 15.0, 16.0, 17.0]
    ema = calculate_ema(prices, period=5)
    assert ema is not None
    assert 13.0 < ema < 17.0

def test_calculate_rsi():
    # Uptrend prices should have high RSI (> 60)
    uptrend = [10.0 + i for i in range(25)]
    rsi_up = calculate_rsi(uptrend, period=14)
    assert rsi_up is not None
    assert rsi_up > 60.0

    # Downtrend prices should have low RSI (< 40)
    downtrend = [50.0 - i for i in range(25)]
    rsi_down = calculate_rsi(downtrend, period=14)
    assert rsi_down is not None
    assert rsi_down < 40.0

def test_evaluate_market_regime():
    # Falling knife scenario
    crash_prices = [100.0 - (i * 2.5) for i in range(30)]
    regime = evaluate_market_regime(crash_prices)
    assert regime["safe_to_buy"] is False
    assert regime["regime"] in ["oversold_dump", "bearish_downtrend"]
