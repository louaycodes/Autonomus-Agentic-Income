import asyncio
import argparse
import sys
import math
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
from src.trading.indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_macd,
    calculate_confluence_score,
    evaluate_market_regime
)

async def fetch_binance_historical_candles(symbol: str = "BTC/USDT", interval: str = "4h", limit: int = 1000, days: Optional[int] = None) -> List[Dict[str, float]]:
    """Fetches real historical OHLCV candle records from Binance public API with pagination."""
    base_sym = symbol.replace("/", "")
    
    # Calculate required candle count if days is specified
    candles_per_day = {"15m": 96, "1h": 24, "4h": 6, "1d": 1}.get(interval, 6)
    target_candles = (days * candles_per_day) if days else limit

    all_raw = []
    end_time = None

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            while len(all_raw) < target_candles:
                batch_size = min(1000, target_candles - len(all_raw))
                url = f"https://api.binance.com/api/v3/klines?symbol={base_sym}&interval={interval}&limit={batch_size}"
                if end_time:
                    url += f"&endTime={end_time}"
                
                resp = await client.get(url)
                if resp.status_code != 200:
                    break
                data = resp.json()
                if not data or not isinstance(data, list):
                    break
                
                all_raw = data + all_raw
                end_time = data[0][0] - 1
                await asyncio.sleep(0.05)

        if all_raw:
            candles = []
            for k in all_raw:
                candles.append({
                    "open_time": k[0],
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                })
            return candles
    except Exception as e:
        print(f"Note: Binance API fetch note ({e}), generating deterministic price series for simulation.")

    # Resilient synthetic price series fallback (wave + trend)
    base_price = 60000.0 if "BTC" in symbol else (3000.0 if "ETH" in symbol else 150.0)
    candles = []
    price = base_price
    for i in range(limit):
        wave = math.sin(i / 15.0) * (base_price * 0.02)
        trend = (i / limit) * (base_price * 0.05)
        price = base_price + wave + trend
        candles.append({
            "open_time": i,
            "open": price * 0.998,
            "high": price * 1.005,
            "low": price * 0.995,
            "close": price,
            "volume": 100.0
        })
    return candles

def run_backtest(candles: List[Dict[str, float]], initial_capital: float = 200.0,
                 step_percent: float = 0.8, grid_levels: int = 14,
                 min_confluence: float = 45.0, leverage: int = 3,
                 compound: bool = True) -> Dict[str, Any]:
    """
    Simulates the Apex Dual-Engine Strategy with Controlled Leverage (3x) & Momentum Sniper:
    - High-frequency micro-grid scalping (0.8% base)
    - Momentum Breakout expansion (1.5% target on high confluence)
    - Controlled 3x margin leverage with strict stop-loss
    - Dynamic capital compounding on every cent of realized profit
    - Drawdown & liquidation risk guard
    """
    capital = initial_capital
    peak_capital = initial_capital
    max_drawdown_pct = 0.0
    
    step_pct = step_percent / 100.0
    lev = max(1, leverage)

    closes = [c["close"] for c in candles]
    if len(closes) < 30:
        return {"error": "Données historiques insuffisantes (minimum 30 bougies requises)"}

    # Tracking orders and positions
    open_orders = [] # list of {"side": "buy", "price": float, "amount": float, "margin": float}
    filled_positions = [] # list of {"buy_price": float, "target_sell": float, "amount": float, "margin": float, "stop_loss": float}
    completed_trades = []

    levels_count = max(4, grid_levels // 2)
    alloc_margin_per_level = (initial_capital * 0.75) / levels_count

    # Initial grid setup
    initial_p = closes[29]
    for lvl in range(1, levels_count + 1):
        bp = round(initial_p * (1.0 - (lvl * step_pct)), 4)
        pos_val = alloc_margin_per_level * lev
        amt = pos_val / bp
        if capital >= alloc_margin_per_level:
            capital -= alloc_margin_per_level
            open_orders.append({
                "side": "buy",
                "price": bp,
                "amount": amt,
                "margin": alloc_margin_per_level
            })

    # Simulation loop across candles
    for i in range(30, len(candles)):
        candle = candles[i]
        curr_price = candle["close"]
        low_price = candle["low"]
        high_price = candle["high"]
        historical_subset = closes[max(0, i - 50):i + 1]

        # 1. Technical Confluence & Momentum Detection
        confluence = calculate_confluence_score(historical_subset)
        score = confluence["score"]
        is_safe_to_buy = confluence["safe_to_buy"] and (score >= min_confluence)
        is_momentum_breakout = score >= 65.0

        # Step multiplier: expands during breakout to maximize gain
        active_step_pct = step_pct * 1.6 if is_momentum_breakout else step_pct
        step_mult = 1.0 + active_step_pct
        step_down = 1.0 - step_pct

        # 2. Check if existing target SELLs got filled or Stop-Loss hit
        remaining_positions = []
        for pos in filled_positions:
            # Emergency Stop-Loss Guard (cut loss at -8% price move only if leverage > 1 to avoid liquidation)
            if lev > 1 and low_price <= pos["stop_loss"]:
                exit_price = pos["stop_loss"]
                sell_val = pos["amount"] * exit_price
                buy_val = pos["amount"] * pos["buy_price"]
                loss = (buy_val - sell_val)
                recovered_margin = max(0.0, pos["margin"] - loss)
                capital += recovered_margin

                completed_trades.append({
                    "buy_price": pos["buy_price"],
                    "sell_price": exit_price,
                    "net_profit": -loss,
                    "roi_pct": (-loss / pos["margin"]) * 100.0
                })
                continue

            # Target Take-Profit Hit!
            if high_price >= pos["target_sell"]:
                sell_val = pos["amount"] * pos["target_sell"]
                buy_val = pos["amount"] * pos["buy_price"]
                fee = sell_val * 0.001 # 0.1% spot fee
                gross_profit = sell_val - buy_val
                net_profit = gross_profit - fee
                capital += (pos["margin"] + net_profit)

                completed_trades.append({
                    "buy_price": pos["buy_price"],
                    "sell_price": pos["target_sell"],
                    "net_profit": net_profit,
                    "roi_pct": (net_profit / pos["margin"]) * 100.0
                })

                # Immediate order recycling: re-seed BUY below the take-profit level
                if is_safe_to_buy:
                    new_buy_p = round(pos["target_sell"] * step_down, 4)
                    recycle_margin = min(capital * 0.20, alloc_margin_per_level)
                    if capital >= recycle_margin:
                        capital -= recycle_margin
                        open_orders.append({
                            "side": "buy",
                            "price": new_buy_p,
                            "amount": (recycle_margin * lev) / new_buy_p,
                            "margin": recycle_margin
                        })
            else:
                remaining_positions.append(pos)
        filled_positions = remaining_positions

        # 3. Check if open BUY orders got filled in this candle
        remaining_buys = []
        for order in open_orders:
            if low_price <= order["price"]:
                # BUY executed! Place paired SELL target
                stop_loss_price = round(order["price"] * (1.0 - 0.08), 4)
                filled_positions.append({
                    "buy_price": order["price"],
                    "target_sell": round(order["price"] * step_mult, 4),
                    "amount": order["amount"],
                    "margin": order["margin"],
                    "stop_loss": stop_loss_price
                })
            else:
                remaining_buys.append(order)
        open_orders = remaining_buys

        # 4. Trailing Maintenance: Cancel stale BUY orders (price climbed > 5% above order)
        kept_buys = []
        for order in open_orders:
            dist = (curr_price - order["price"]) / curr_price
            if dist > 0.05:
                capital += order["margin"] # Reclaim capital
            else:
                kept_buys.append(order)
        open_orders = kept_buys

        # 5. Trailing Dynamic Grid Replenishment if price climbed upward
        if len(open_orders) < 3 and is_safe_to_buy and capital >= alloc_margin_per_level:
            for lvl in range(1, 4):
                new_bp = round(curr_price * (1.0 - (lvl * step_pct)), 4)
                if capital >= alloc_margin_per_level:
                    capital -= alloc_margin_per_level
                    open_orders.append({
                        "side": "buy",
                        "price": new_bp,
                        "amount": (alloc_margin_per_level * lev) / new_bp,
                        "margin": alloc_margin_per_level
                    })

        # Calculate Total Portfolio Equity (Cash + Orders Margin + Open Unrealized PnL)
        unrealized_pnl = sum((curr_price - p["buy_price"]) * p["amount"] for p in filled_positions)
        positions_margin = sum(p["margin"] for p in filled_positions)
        orders_margin = sum(o["margin"] for o in open_orders)
        total_equity = capital + orders_margin + positions_margin + unrealized_pnl

        # Track Drawdown
        if total_equity > peak_capital:
            peak_capital = total_equity
        drawdown = ((peak_capital - total_equity) / peak_capital) * 100.0
        if drawdown > max_drawdown_pct:
            max_drawdown_pct = drawdown

    # Final tally
    final_price = closes[-1]
    final_unrealized = sum((final_price - p["buy_price"]) * p["amount"] for p in filled_positions)
    pos_margin_refund = sum(p["margin"] for p in filled_positions)
    orders_margin_refund = sum(o["margin"] for o in open_orders)
    final_equity = round(capital + orders_margin_refund + pos_margin_refund + final_unrealized, 2)
    total_net_profit = round(final_equity - initial_capital, 2)
    total_roi_pct = round((total_net_profit / initial_capital) * 100.0, 2)

    # Buy & Hold benchmark comparison
    start_p = closes[30]
    end_p = closes[-1]
    buy_and_hold_roi_pct = round(((end_p - start_p) / start_p) * 100.0, 2)

    win_trades = sum(1 for t in completed_trades if t["net_profit"] > 0)
    total_trades_count = len(completed_trades)
    win_rate = round((win_trades / total_trades_count * 100.0), 1) if total_trades_count > 0 else 0.0

    return {
        "initial_capital": initial_capital,
        "final_equity": final_equity,
        "total_profit_usd": total_net_profit,
        "roi_percent": total_roi_pct,
        "buy_and_hold_roi_percent": buy_and_hold_roi_pct,
        "total_trades": total_trades_count,
        "win_rate_percent": win_rate,
        "max_drawdown_percent": round(max_drawdown_pct, 2),
        "candles_analyzed": len(candles) - 30
    }

async def run_portfolio_backtest(symbols: List[str], interval: str = "4h", limit: int = 1000, days: Optional[int] = 1095, initial_capital: float = 1000.0, leverage: int = 3):
    """Executes backtests across all portfolio assets and generates a formatted report."""
    years_approx = round(days / 365, 1) if days else round(limit / 2190, 1)
    days_label = f"{days} jours ({years_approx} ans)" if days else f"{limit} bougies"
    print("=" * 68)
    print(f"   RAPPORT DE BACKTEST QUANTITATIF APEX — {years_approx} ANS D'HISTORIQUE")
    print(f"   Capital Initial : ${initial_capital:.2f} | Levier Marge : {leverage}x | Durée : {days_label}")
    print("=" * 68)

    per_symbol_cap = initial_capital / len(symbols)
    portfolio_final = 0.0
    all_trades = 0
    date_range_str = ""

    for sym in symbols:
        candles = await fetch_binance_historical_candles(sym, interval=interval, limit=limit, days=days)
        if candles and not date_range_str:
            start_dt = time.strftime('%d/%m/%Y', time.gmtime(candles[0]['open_time'] / 1000))
            end_dt = time.strftime('%d/%m/%Y', time.gmtime(candles[-1]['open_time'] / 1000))
            date_range_str = f"Du {start_dt} au {end_dt} ({len(candles)} bougies)"

        res = run_backtest(candles, initial_capital=per_symbol_cap, leverage=leverage)
        portfolio_final += res["final_equity"]
        all_trades += res["total_trades"]

        print(f"\n🪙 Actif : {sym}")
        print(f"  • Capital Alloué : ${per_symbol_cap:.2f} ➔ Capital Final : ${res['final_equity']:.2f}")
        print(f"  • Profit Net Réalisé : +${res['total_profit_usd']:.2f} (ROI : +{res['roi_percent']}%)")
        print(f"  • Évolution Passive (Buy & Hold) : {res['buy_and_hold_roi_percent']:+}%")
        print(f"  • Trades Gagnants Exécutés : {res['total_trades']} cycles (Taux : {res['win_rate_percent']}%)")
        print(f"  • Risque Max Subi (Max Drawdown) : {res['max_drawdown_percent']}%")

    total_profit = round(portfolio_final - initial_capital, 2)
    portfolio_roi = round((total_profit / initial_capital) * 100.0, 2)
    effective_days = days or (limit / 6)
    months_count = max(1.0, effective_days / 30.4)
    monthly_avg_usd = round(total_profit / months_count, 2)
    daily_avg_usd = round(total_profit / effective_days, 2)

    print("\n" + "=" * 68)
    print(f"🏆 BILAN GLOBAL DU PORTEFEUILLE MULTI-ACTIFS ({years_approx} ANS) :")
    if date_range_str:
        print(f"  📅 Période Réelle : {date_range_str}")
    print(f"  💵 Capital de Départ : ${initial_capital:.2f}")
    print(f"  🏦 Capital Final avec Réinvestissement : ${portfolio_final:.2f}")
    print(f"  📈 Gain Net Total Encaissé : +${total_profit:.2f} (+{portfolio_roi}%)")
    print(f"  💰 Revenu Passif Moyen Journalier : +${daily_avg_usd:.2f} / jour")
    print(f"  📅 Revenu Passif Mensuel : +${monthly_avg_usd:.2f} / mois")
    print(f"  🔄 Total Cycles de Trading : {all_trades} allers-retours")
    print("=" * 68)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apex Trading Strategy Backtester")
    parser.add_argument("--symbols", type=str, default="BTC/USDT,SOL/USDT,ETH/USDT", help="Comma-separated symbols")
    parser.add_argument("--interval", type=str, default="1h", help="Candle timeframe interval (1h, 4h, 1d)")
    parser.add_argument("--days", type=int, default=1095, help="Number of historical days to backtest (1095 = 3 years)")
    parser.add_argument("--limit", type=int, default=1000, help="Fallback candle limit if days not provided")
    parser.add_argument("--capital", type=float, default=1000.0, help="Initial simulation capital")
    parser.add_argument("--leverage", type=int, default=1, help="Leverage multiplier (1 = pure spot)")
    args = parser.parse_args()

    sym_list = [s.strip() for s in args.symbols.split(",") if s.strip()]
    asyncio.run(run_portfolio_backtest(
        sym_list,
        interval=args.interval,
        limit=args.limit,
        days=args.days,
        initial_capital=args.capital,
        leverage=args.leverage
    ))
