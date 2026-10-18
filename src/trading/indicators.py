"""Technical Indicators & Market Regime Analysis (Pure Python, Zero Heavy Bloat)."""
from typing import List, Dict, Any, Optional

def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """Calculates Exponential Moving Average (EMA)."""
    if len(prices) < period:
        return None
    multiplier = 2.0 / (period + 1)
    # Start with Simple Moving Average for the first period
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """Calculates Relative Strength Index (RSI)."""
    if len(prices) <= period:
        return None

    gains = []
    losses = []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        if delta >= 0:
            gains.append(delta)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(delta))

    if len(gains) < period:
        return None

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(rsi, 2)

def evaluate_market_regime(closes: List[float]) -> Dict[str, Any]:
    """
    Evaluates whether the market is in Safe Range, Bullish Trend, or Dangerous Free-fall.
    Returns safe_to_buy boolean and technical details.
    """
    if len(closes) < 20:
        # Not enough history, default to neutral range trading
        return {"regime": "range", "safe_to_buy": True, "rsi": 50.0, "ema_short": None, "ema_long": None}

    raw_rsi = calculate_rsi(closes, period=14)
    rsi = raw_rsi if raw_rsi is not None else 50.0
    ema_short = calculate_ema(closes, period=min(20, len(closes)))
    ema_long = calculate_ema(closes, period=min(50, len(closes)))

    current_price = closes[-1]
    safe_to_buy = True
    regime = "range"

    # Extreme Oversold Crash Detection (Falling Knife Guard)
    if rsi < 25.0:
        regime = "oversold_dump"
        safe_to_buy = False  # Wait for stabilization, do not catch falling knives

    elif ema_short and ema_long:
        if current_price > ema_short > ema_long:
            regime = "bullish_uptrend"
            safe_to_buy = True
        elif current_price < ema_short < ema_long and rsi < 35.0:
            regime = "bearish_downtrend"
            safe_to_buy = False
        else:
            regime = "range"
            safe_to_buy = True

    return {
        "regime": regime,
        "safe_to_buy": safe_to_buy,
        "rsi": rsi,
        "ema_short": round(ema_short, 4) if ema_short else None,
        "ema_long": round(ema_long, 4) if ema_long else None
    }
