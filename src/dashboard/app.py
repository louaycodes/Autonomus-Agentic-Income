"""Web Dashboard Backend for APEX Trading Bot — 100% Tunisian Dinar (DT)."""
import os
import sqlite3
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard")

app = FastAPI(title="APEX Trading Bot Dashboard (Dinar Tunisien)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
DB_NAME = os.getenv("DB_NAME", "trading.db")
DB_PATH = DATA_DIR / DB_NAME
DT_RATE = float(os.getenv("DT_RATE", "3.10"))  # 1 USD = 3.10 DT

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

# Cached market prices to ensure instant API responses
_cached_prices: Dict[str, float] = {
    "BTC": 77700.0,
    "SOL": 93.5,
    "ETH": 2295.0,
}
_last_price_fetch_ts: float = 0.0


async def fetch_live_prices() -> Dict[str, float]:
    """Fetches real-time crypto prices with scoped symbol querying and fallback caching."""
    global _cached_prices, _last_price_fetch_ts
    import time
    now = time.time()
    if now - _last_price_fetch_ts < 4.0:
        return _cached_prices

    symbols_map = {"BTCUSDT": "BTC", "SOLUSDT": "SOL", "ETHUSDT": "ETH"}
    try:
        async with httpx.AsyncClient(timeout=3.5) as client:
            resp = await client.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbols": '["BTCUSDT","SOLUSDT","ETHUSDT"]'}
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data:
                    sym = item.get("symbol")
                    if sym in symbols_map:
                        _cached_prices[symbols_map[sym]] = float(item.get("price", 0.0))
                _last_price_fetch_ts = now
    except Exception as e:
        logger.debug(f"Live price fetch note: {e}")

    return _cached_prices


def get_db_connection() -> sqlite3.Connection:
    """Connects to SQLite in read-only mode to prevent write contention."""
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="La base de données du bot n'est pas encore initialisée.")
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON;")
        return conn
    except Exception as e:
        conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "currency": "DT", "rate": DT_RATE}


@app.get("/api/status")
async def get_dashboard_status() -> Dict[str, Any]:
    """Aggregates all trading performance and portfolio metrics converted into Dinars Tunisiens (DT)."""
    prices_usd = await fetch_live_prices()
    conn = get_db_connection()

    try:
        # 1. Bot State & Wallet Balances
        bot_state_rows = conn.execute("SELECT key, value FROM bot_state").fetchall()
        bot_state = {r["key"]: r["value"] for r in bot_state_rows}

        capital_usd = float(bot_state.get("current_capital_usd", 9675.0))
        free_usdt = float(bot_state.get("paper_balance_usdt", 0.0))

        raw_crypto = bot_state.get("paper_balance_crypto", "{}")
        try:
            crypto_balances = json.loads(raw_crypto)
        except Exception:
            crypto_balances = {"BTC": 0.0, "SOL": 0.0, "ETH": 0.0}

        # 2. Open Orders & Locked Capital
        orders_rows = conn.execute(
            "SELECT order_id, symbol, side, price, amount, cost_usd, created_at FROM grid_orders WHERE status='open' ORDER BY created_at DESC"
        ).fetchall()

        locked_usdt = sum(float(o["cost_usd"]) for o in orders_rows if o["side"] == "buy")

        open_buys = []
        open_sells = []
        for o in orders_rows:
            side = o["side"]
            sym = o["symbol"]
            base = sym.split("/")[0]
            price_usd = float(o["price"])
            price_dt = round(price_usd * DT_RATE, 2)
            cost_usd = float(o["cost_usd"])
            cost_dt = round(cost_usd * DT_RATE, 2)
            amount = float(o["amount"])

            item = {
                "order_id": o["order_id"],
                "symbol": sym,
                "base": base,
                "side": side,
                "price_dt": price_dt,
                "amount": amount,
                "total_dt": cost_dt,
                "created_at": o["created_at"],
            }
            if side == "buy":
                open_buys.append(item)
            else:
                open_sells.append(item)

        # 3. Crypto Portfolio Valuation in DT
        crypto_assets = []
        total_crypto_usd = 0.0

        names_map = {
            "BTC": ("Bitcoin", "₿", "#F7931A"),
            "SOL": ("Solana", "◎", "#14F195"),
            "ETH": ("Ethereum", "Ξ", "#627EEA"),
        }

        for base, amount in crypto_balances.items():
            amt = float(amount)
            p_usd = prices_usd.get(base, 0.0)
            val_usd = amt * p_usd
            total_crypto_usd += val_usd
            name, icon, color = names_map.get(base, (base, "🪙", "#3B82F6"))

            crypto_assets.append({
                "symbol": base,
                "name": name,
                "icon": icon,
                "color": color,
                "amount": round(amt, 6 if base == "BTC" else 4),
                "price_dt": round(p_usd * DT_RATE, 2),
                "value_dt": round(val_usd * DT_RATE, 2),
            })

        # 4. Total Net Portfolio in DT
        free_cash_dt = round(free_usdt * DT_RATE, 2)
        locked_cash_dt = round(locked_usdt * DT_RATE, 2)
        crypto_total_dt = round(total_crypto_usd * DT_RATE, 2)
        portfolio_total_dt = round((free_usdt + locked_usdt + total_crypto_usd) * DT_RATE, 2)
        referent_capital_dt = round(capital_usd * DT_RATE, 2)

        # 5. Completed Trades (Today & History)
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        today_pnl_row = conn.execute(
            "SELECT net_profit_usd, trades_count, volume_usd FROM daily_pnl WHERE date = ?", (today_str,)
        ).fetchone()

        profit_today_usd = float(today_pnl_row["net_profit_usd"]) if today_pnl_row else 0.0
        trades_today_count = int(today_pnl_row["trades_count"]) if today_pnl_row else 0
        volume_today_usd = float(today_pnl_row["volume_usd"]) if today_pnl_row else 0.0

        profit_today_dt = round(profit_today_usd * DT_RATE, 2)
        volume_today_dt = round(volume_today_usd * DT_RATE, 2)

        # All-time profit & completed trades count
        all_time_profit_row = conn.execute(
            "SELECT COALESCE(SUM(net_profit_usd), 0.0) as total_profit, COALESCE(SUM(volume_usd), 0.0) as total_vol FROM daily_pnl"
        ).fetchone()

        total_profit_usd = float(all_time_profit_row["total_profit"] or 0.0)
        total_profit_dt = round(total_profit_usd * DT_RATE, 2)

        total_trades_count = conn.execute("SELECT COUNT(*) FROM completed_trades").fetchone()[0]

        # Return on Capital Today %
        profit_today_pct = round((profit_today_usd / max(1.0, capital_usd)) * 100, 2)

        # 6. Recent Completed Trades List (last 15)
        recent_trades_rows = conn.execute(
            """
            SELECT trade_id, symbol, buy_price, sell_price, amount, net_profit_usd, roi_percent, timestamp
            FROM completed_trades
            ORDER BY timestamp DESC
            LIMIT 15
            """
        ).fetchall()

        recent_trades = []
        for t in recent_trades_rows:
            sym = t["symbol"]
            base = sym.split("/")[0]
            name, icon, _ = names_map.get(base, (base, "🪙", "#3B82F6"))

            b_price_dt = round(float(t["buy_price"]) * DT_RATE, 2)
            s_price_dt = round(float(t["sell_price"]) * DT_RATE, 2)
            p_usd = float(t["net_profit_usd"])
            p_dt = round(p_usd * DT_RATE, 2)

            # Format human timestamp
            ts_str = t["timestamp"]
            formatted_time = ""
            try:
                dt_obj = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                formatted_time = dt_obj.strftime("%d/%m à %H:%M")
            except Exception:
                formatted_time = ts_str[:16]

            recent_trades.append({
                "trade_id": t["trade_id"],
                "symbol": sym,
                "asset_name": name,
                "icon": icon,
                "buy_price_dt": b_price_dt,
                "sell_price_dt": s_price_dt,
                "profit_dt": p_dt,
                "is_positive": p_dt >= 0,
                "roi_percent": float(t["roi_percent"]),
                "formatted_time": formatted_time,
                "amount": float(t["amount"]),
            })

        # 7. Daily History for Charts (last 10 days)
        history_rows = conn.execute(
            "SELECT date, net_profit_usd, trades_count FROM daily_pnl ORDER BY date DESC LIMIT 10"
        ).fetchall()

        daily_chart_labels = []
        daily_chart_values = []
        dates_in_history = [h["date"] for h in history_rows]

        for h in reversed(history_rows):
            d_str = h["date"]
            try:
                d_formatted = datetime.strptime(d_str, "%Y-%m-%d").strftime("%d/%m")
            except Exception:
                d_formatted = d_str[-5:]
            daily_chart_labels.append(d_formatted)
            daily_chart_values.append(round(float(h["net_profit_usd"]) * DT_RATE, 2))

        # Ensure today is always present in chart
        if today_str not in dates_in_history:
            today_formatted = datetime.now(timezone.utc).strftime("%d/%m")
            daily_chart_labels.append(today_formatted)
            daily_chart_values.append(profit_today_dt)

        # 8. Bot Health & Operational State
        is_bot_active = len(orders_rows) > 0 or len(recent_trades) > 0

        return {
            "status": "actif" if is_bot_active else "en_attente",
            "currency": "DT",
            "dt_rate": DT_RATE,
            "portfolio": {
                "total_dt": portfolio_total_dt,
                "referent_capital_dt": referent_capital_dt,
                "free_cash_dt": free_cash_dt,
                "locked_cash_dt": locked_cash_dt,
                "crypto_total_dt": crypto_total_dt,
                "crypto_ratio_pct": round((crypto_total_dt / max(1.0, portfolio_total_dt)) * 100, 1),
                "cash_ratio_pct": round(((free_cash_dt + locked_cash_dt) / max(1.0, portfolio_total_dt)) * 100, 1),
            },
            "performance": {
                "profit_today_dt": profit_today_dt,
                "profit_today_pct": profit_today_pct,
                "trades_today_count": trades_today_count,
                "volume_today_dt": volume_today_dt,
                "total_profit_dt": total_profit_dt,
                "total_trades_count": total_trades_count,
            },
            "crypto_assets": crypto_assets,
            "recent_trades": recent_trades,
            "open_orders": {
                "total_count": len(orders_rows),
                "buys": open_buys,
                "sells": open_sells,
            },
            "daily_chart": {
                "labels": daily_chart_labels,
                "values": daily_chart_values,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    finally:
        conn.close()


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the single-page responsive mobile dashboard."""
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Template non trouvé.")
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8085"))
    uvicorn.run("src.dashboard.app:app", host="0.0.0.0", port=port, reload=False)

