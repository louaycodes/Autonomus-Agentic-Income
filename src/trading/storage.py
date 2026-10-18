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

    def save_order(self, order_id: str, side: str, price: float, amount: float,
                   cost_usd: float, status: str = "open", pair_order_id: Optional[str] = None) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO grid_orders 
                (order_id, side, price, amount, cost_usd, status, pair_order_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                    status = excluded.status,
                    pair_order_id = COALESCE(excluded.pair_order_id, grid_orders.pair_order_id),
                    updated_at = excluded.updated_at
                """,
                (order_id, side, price, amount, cost_usd, status, pair_order_id, now_iso, now_iso)
            )

    def get_open_orders(self, side: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            query = "SELECT * FROM grid_orders WHERE status = 'open'"
            params = []
            if side:
                query += " AND side = ?"
                params.append(side)
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
                               amount: float, fee_usd: float = 0.0) -> Dict[str, Any]:
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
                (trade_id, buy_price, sell_price, amount, gross_profit_usd, fee_usd, net_profit_usd, roi_percent, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (trade_id, buy_price, sell_price, amount, gross_profit, fee_usd, net_profit, roi_pct, now_iso)
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

        return {
            "trade_id": trade_id,
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
