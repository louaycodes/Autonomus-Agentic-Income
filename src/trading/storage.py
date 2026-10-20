"""Persistent Storage Layer — SQLite in WAL Mode for Quantitative Trading."""
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

class TradingDatabase:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self.get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS grid_orders (
                order_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL DEFAULT 'BTC/USDT',
                side TEXT NOT NULL,
                price REAL NOT NULL,
                amount REAL NOT NULL,
                cost_usd REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                pair_order_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS completed_trades (
                trade_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL DEFAULT 'BTC/USDT',
                buy_price REAL NOT NULL,
                sell_price REAL NOT NULL,
                amount REAL NOT NULL,
                gross_profit_usd REAL NOT NULL,
                fee_usd REAL NOT NULL,
                net_profit_usd REAL NOT NULL,
                roi_percent REAL NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS daily_pnl (
                date TEXT PRIMARY KEY,
                net_profit_usd REAL NOT NULL DEFAULT 0.0,
                trades_count INTEGER NOT NULL DEFAULT 0,
                volume_usd REAL NOT NULL DEFAULT 0.0,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bot_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)

            # Safe column migrations if database already existed
            try:
                conn.execute("ALTER TABLE grid_orders ADD COLUMN symbol TEXT DEFAULT 'BTC/USDT'")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE completed_trades ADD COLUMN symbol TEXT DEFAULT 'BTC/USDT'")
            except sqlite3.OperationalError:
                pass

    def get_capital(self) -> float:
        """Retrieves active trading capital, compounding accumulated profits."""
        from src.trading.config import config
        stored = self.get_state("current_capital_usd")
        if stored is not None:
            try:
                return float(stored)
            except ValueError:
                pass
        initial = float(config.total_capital_usd)
        self.set_state("current_capital_usd", initial)
        return initial

    def set_capital(self, capital_usd: float) -> float:
        """Sets or resets the base working capital."""
        val = round(float(capital_usd), 4)
        self.set_state("current_capital_usd", val)
        return val

    def add_capital(self, profit_usd: float) -> float:
        """Adds realized profit (every cent) directly into active working capital."""
        current = self.get_capital()
        new_capital = round(current + profit_usd, 4)
        self.set_state("current_capital_usd", new_capital)
        return new_capital

    def reset_database(self, initial_capital: Optional[float] = None) -> None:
        """Resets all orders, trades, and pnl metrics to start fresh from zero."""
        from src.trading.config import config
        cap = float(initial_capital if initial_capital is not None else config.total_capital_usd)
        with self.get_connection() as conn:
            conn.execute("DELETE FROM grid_orders;")
            conn.execute("DELETE FROM completed_trades;")
            conn.execute("DELETE FROM daily_pnl;")
            conn.execute("DELETE FROM bot_state;")
        self.set_capital(cap)
        self.set_state("paper_balance_usdt", cap)
        initial_crypto = {s.split("/")[0]: 0.0 for s in config.symbols}
        self.set_state("paper_balance_crypto", json.dumps(initial_crypto))

    def save_order(self, order_id: str, side: str, price: float, amount: float,
                   cost_usd: float, status: str = "open", pair_order_id: Optional[str] = None,
                   symbol: str = "BTC/USDT") -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO grid_orders 
                (order_id, symbol, side, price, amount, cost_usd, status, pair_order_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                    symbol = excluded.symbol,
                    status = excluded.status,
                    pair_order_id = COALESCE(excluded.pair_order_id, grid_orders.pair_order_id),
                    updated_at = excluded.updated_at
                """,
                (order_id, symbol, side, price, amount, cost_usd, status, pair_order_id, now_iso, now_iso)
            )

    def get_open_orders(self, side: Optional[str] = None, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            query = "SELECT * FROM grid_orders WHERE status = 'open'"
            params = []
            if side:
                query += " AND side = ?"
                params.append(side)
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            query += " ORDER BY price ASC"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def update_order_status(self, order_id: str, status: str) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE grid_orders SET status = ?, updated_at = ? WHERE order_id = ?",
                (status, now_iso, order_id)
            )

    def record_completed_trade(self, trade_id: str, buy_price: float, sell_price: float,
                               amount: float, fee_usd: float = 0.0, symbol: str = "BTC/USDT") -> Dict[str, Any]:
        from src.trading.config import config
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        now_iso = now.isoformat()

        buy_cost = buy_price * amount
        sell_cost = sell_price * amount
        gross_profit = sell_cost - buy_cost
        net_profit = round(gross_profit - fee_usd, 4)
        roi_pct = round((net_profit / buy_cost) * 100, 2) if buy_cost > 0 else 0.0

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO completed_trades 
                (trade_id, symbol, buy_price, sell_price, amount, gross_profit_usd, fee_usd, net_profit_usd, roi_percent, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (trade_id, symbol, buy_price, sell_price, amount, gross_profit, fee_usd, net_profit, roi_pct, now_iso)
            )

            # Update Daily PnL atomically
            conn.execute(
                """
                INSERT INTO daily_pnl (date, net_profit_usd, trades_count, volume_usd, updated_at)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    net_profit_usd = net_profit_usd + excluded.net_profit_usd,
                    trades_count = trades_count + 1,
                    volume_usd = volume_usd + excluded.volume_usd,
                    updated_at = excluded.updated_at
                """,
                (today, net_profit, sell_cost, now_iso)
            )

        # Automatically compound every cent earned into trading capital
        if config.compound_profits and net_profit > 0:
            self.add_capital(net_profit)

        return {
            "trade_id": trade_id,
            "symbol": symbol,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "net_profit_usd": net_profit,
            "roi_percent": roi_pct
        }

    def get_daily_pnl(self, date_str: str) -> Dict[str, Any]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM daily_pnl WHERE date = ?", (date_str,)).fetchone()
            if row:
                return dict(row)
            return {
                "date": date_str,
                "net_profit_usd": 0.0,
                "trades_count": 0,
                "volume_usd": 0.0,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

    def get_all_time_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            pnl_totals = conn.execute(
                """
                SELECT 
                    SUM(net_profit_usd) as total_profit,
                    SUM(trades_count) as total_trades,
                    SUM(volume_usd) as total_volume
                FROM daily_pnl
                """
            ).fetchone()
            open_count = conn.execute("SELECT COUNT(*) FROM grid_orders WHERE status = 'open'").fetchone()[0]

            return {
                "total_profit_usd": round(pnl_totals["total_profit"] or 0.0, 2),
                "total_trades": pnl_totals["total_trades"] or 0,
                "total_volume_usd": round(pnl_totals["total_volume"] or 0.0, 2),
                "open_grid_orders": open_count
            }

    def set_state(self, key: str, value: Any) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO bot_state (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, str(value), now_iso)
            )

    def get_state(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT value FROM bot_state WHERE key = ?", (key,)).fetchone()
            if row:
                return row["value"]
            return default
