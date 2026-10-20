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

def calculate_macd(prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, Optional[float]]:
    """Calculates Moving Average Convergence Divergence (MACD), Signal line, and Histogram."""
    if len(prices) < slow_period + signal_period:
        return {"macd": None, "signal": None, "histogram": None}

    # Calculate EMA fast and slow across time series
    fast_mult = 2.0 / (fast_period + 1)
    slow_mult = 2.0 / (slow_period + 1)

    fast_ema = sum(prices[:fast_period]) / fast_period
    slow_ema = sum(prices[:slow_period]) / slow_period

    # Keep track of fast EMA values aligned with slow EMA start
    fast_history = [fast_ema]
    for p in prices[fast_period:slow_period]:
        fast_ema = (p - fast_ema) * fast_mult + fast_ema
        fast_history.append(fast_ema)

    macd_series = []
    for i in range(slow_period, len(prices)):
        p = prices[i]
        fast_ema = (p - fast_ema) * fast_mult + fast_ema
        slow_ema = (p - slow_ema) * slow_mult + slow_ema
        macd_series.append(fast_ema - slow_ema)

    if len(macd_series) < signal_period:
        return {"macd": round(macd_series[-1], 4) if macd_series else None, "signal": None, "histogram": None}

    # Signal line is EMA of MACD series
    sig_mult = 2.0 / (signal_period + 1)
    sig_ema = sum(macd_series[:signal_period]) / signal_period
    for m in macd_series[signal_period:]:
        sig_ema = (m - sig_ema) * sig_mult + sig_ema

    curr_macd = macd_series[-1]
    curr_hist = curr_macd - sig_ema
    return {
        "macd": round(curr_macd, 4),
        "signal": round(sig_ema, 4),
        "histogram": round(curr_hist, 4)
    }

def find_support_resistance_zones(prices: List[float], window: int = 3) -> Dict[str, List[float]]:
    """
    Finds verified price support and resistance bounce levels (Swing Points).
    Clusters nearby points within 0.5% into significant zones.
    """
    if len(prices) < window * 2 + 1:
        return {"support_zones": [], "resistance_zones": []}

    supports = []
    resistances = []

    for i in range(window, len(prices) - window):
        center = prices[i]
        is_min = all(center <= prices[j] for j in range(i - window, i + window + 1))
        is_max = all(center >= prices[j] for j in range(i - window, i + window + 1))

        if is_min:
            supports.append(center)
        if is_max:
            resistances.append(center)

    # Dedup and sort
    def cluster_levels(levels: List[float]) -> List[float]:
        if not levels:
            return []
        sorted_lvls = sorted(levels)
        clustered = [sorted_lvls[0]]
        for lvl in sorted_lvls[1:]:
            # If within 0.7% of previous cluster, average them
            if abs(lvl - clustered[-1]) / clustered[-1] < 0.007:
                clustered[-1] = round((clustered[-1] + lvl) / 2.0, 4)
            else:
                clustered.append(round(lvl, 4))
        return clustered

    return {
        "support_zones": cluster_levels(supports)[-3:],       # 3 most recent verified supports
        "resistance_zones": cluster_levels(resistances)[-3:]  # 3 most recent verified resistances
    }

def calculate_confluence_score(closes: List[float], macro_trend: str = "bullish") -> Dict[str, Any]:
    """
    Calculates a Multi-Timeframe Confluence Score (0 to 100) based on the course rules:
    - 25 pts: EMA Trend Direction (Price > EMA20 > EMA50)
    - 25 pts: Momentum Stability (RSI in healthy zone 35-65, not dumped or overheated)
    - 25 pts: MACD Convergence (MACD > Signal or Histogram turning positive)
    - 25 pts: S&R Zone Proximity (Price near a verified bounce support)
    """
    if len(closes) < 25:
        return {"score": 50.0, "safe_to_buy": True, "reasons": ["Données insuffisantes, score neutre"]}

    current_price = closes[-1]
    score = 0.0
    reasons = []

    # 1. EMA Structure
    ema20 = calculate_ema(closes, 20)
    ema50 = calculate_ema(closes, min(50, len(closes)))
    if ema20 and ema50:
        if current_price > ema20 and ema20 > ema50:
            score += 25.0
            reasons.append("Tendance haussière confirmée (Prix > EMA20 > EMA50)")
        elif current_price > ema20:
            score += 15.0
            reasons.append("Au-dessus de l'EMA20")
        elif current_price < ema20 < ema50:
            score += 0.0
            reasons.append("Tendance baissière (Sous EMA20 et EMA50)")

    # 2. RSI Assessment
    raw_rsi = calculate_rsi(closes, 14)
    rsi = raw_rsi if raw_rsi is not None else 50.0
    if 35.0 <= rsi <= 65.0:
        score += 25.0
        reasons.append(f"RSI équilibré ({rsi}) sans surchauffe")
    elif 25.0 <= rsi < 35.0:
        score += 15.0
        reasons.append(f"RSI en zone de rebond potentiel ({rsi})")
    elif rsi < 25.0:
        # Crash condition
        score -= 20.0
        reasons.append(f"DANGER: Chute libre extrême (RSI={rsi})")
    elif rsi > 70.0:
        score += 5.0
        reasons.append(f"RSI en surchauffe ({rsi})")

    # 3. MACD Momentum
    macd_data = calculate_macd(closes)
    macd_val = macd_data.get("macd")
    sig_val = macd_data.get("signal")
    hist_val = macd_data.get("histogram")

    if macd_val is not None and sig_val is not None:
        if macd_val > sig_val and (hist_val or 0) > 0:
            score += 25.0
            reasons.append("Accélération haussière confirmée (MACD > Signal et Histogramme > 0)")
        elif macd_val > sig_val:
            score += 15.0
            reasons.append("MACD supérieur au signal")
        else:
            reasons.append("Momentum baissier sur le MACD")

    # 4. Proximity to Support Bounce Zone
    sr_zones = find_support_resistance_zones(closes)
    supports = sr_zones["support_zones"]
    near_support = False
    if supports:
        nearest_sup = max(s for s in supports if s <= current_price * 1.01) if any(s <= current_price * 1.01 for s in supports) else None
        if nearest_sup and abs(current_price - nearest_sup) / current_price <= 0.025:
            near_support = True
            score += 25.0
            reasons.append(f"Proximité d'un palier de rebond vérifié (${nearest_sup:.2f})")
    if not near_support:
        score += 10.0
        reasons.append("Prix en zone intermédiaire")

    # Macro Trend Weighting
    if macro_trend == "bearish":
        score = max(0.0, score - 15.0)
        reasons.append("Pénalité: Tendance générale journalière baissière")
    elif macro_trend == "bullish":
        score = min(100.0, score + 5.0)

    score = max(0.0, min(100.0, round(score, 1)))
    safe_to_buy = score >= 55.0 and rsi >= 25.0

    return {
        "score": score,
        "safe_to_buy": safe_to_buy,
        "rsi": rsi,
        "ema20": round(ema20, 4) if ema20 else None,
        "ema50": round(ema50, 4) if ema50 else None,
        "macd": macd_data,
        "support_zones": sr_zones["support_zones"],
        "resistance_zones": sr_zones["resistance_zones"],
        "reasons": reasons
    }

def evaluate_market_regime(closes: List[float]) -> Dict[str, Any]:
    """
    Evaluates whether the market is in Safe Range, Bullish Trend, or Dangerous Free-fall.
    Returns safe_to_buy boolean and technical details, including confluence scoring.
    """
    if len(closes) < 20:
        return {
            "regime": "range",
            "safe_to_buy": True,
            "rsi": 50.0,
            "ema_short": None,
            "ema_long": None,
            "confluence_score": 50.0
        }

    confluence = calculate_confluence_score(closes)
    rsi = confluence["rsi"]
    ema_short = confluence["ema20"]
    ema_long = confluence["ema50"]
    current_price = closes[-1]

    if rsi < 25.0:
        regime = "oversold_dump"
    elif ema_short and ema_long and current_price > ema_short > ema_long:
        regime = "bullish_uptrend"
    elif ema_short and ema_long and current_price < ema_short < ema_long and rsi < 35.0:
        regime = "bearish_downtrend"
    else:
        regime = "range"

    return {
        "regime": regime,
        "safe_to_buy": confluence["safe_to_buy"],
        "rsi": rsi,
        "ema_short": ema_short,
        "ema_long": ema_long,
        "confluence_score": confluence["score"],
        "confluence_reasons": confluence["reasons"],
        "support_zones": confluence["support_zones"],
        "resistance_zones": confluence["resistance_zones"]
    }
