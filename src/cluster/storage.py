"""Persistent Storage Layer — SQLite in WAL Mode."""
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Crucial WAL mode for concurrent 24/7 operations without lockups
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self.get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                budget_eur REAL,
                deadline TEXT,
                tags TEXT,
                raw_data TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS api_keys (
                key TEXT PRIMARY KEY,
                client_name TEXT NOT NULL,
                tier TEXT NOT NULL DEFAULT 'standard',
                is_active INTEGER NOT NULL DEFAULT 1,
                monthly_quota INTEGER NOT NULL DEFAULT 1000,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS api_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT,
                endpoint TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                revenue_usd REAL NOT NULL DEFAULT 0.0,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS arbitrage_events (
                id TEXT PRIMARY KEY,
                market_id TEXT NOT NULL,
                question TEXT NOT NULL,
                news_source TEXT NOT NULL,
                news_headline TEXT NOT NULL,
                market_price REAL NOT NULL,
                target_price REAL NOT NULL,
                trade_amount_usd REAL NOT NULL,
                profit_usd REAL NOT NULL,
                simulated INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS daily_ledger (
                date TEXT PRIMARY KEY,
                engine_a_revenue REAL NOT NULL DEFAULT 0.0,
                engine_b_revenue REAL NOT NULL DEFAULT 0.0,
                total_revenue REAL NOT NULL DEFAULT 0.0,
                api_requests_count INTEGER NOT NULL DEFAULT 0,
                trades_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            """)

    def save_opportunity(self, opp_id: str, title: str, source: str, category: str,
                         budget_eur: Optional[float], deadline: Optional[str],
                         tags: List[str], raw_data: Dict[str, Any]) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO opportunities 
                (id, title, source, category, budget_eur, deadline, tags, raw_data, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opp_id, title, source, category, budget_eur, deadline,
                    ",".join(tags), json.dumps(raw_data),
                    datetime.now(timezone.utc).isoformat()
                )
            )
            return cursor.rowcount > 0

    def get_opportunities(self, limit: int = 50, offset: int = 0, category: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            query = "SELECT * FROM opportunities"
            params: List[Any] = []
            if category:
                query += " WHERE category = ?"
                params.append(category)
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            rows = conn.execute(query, params).fetchall()
            return [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "source": r["source"],
                    "category": r["category"],
                    "budget_eur": r["budget_eur"],
                    "deadline": r["deadline"],
                    "tags": r["tags"].split(",") if r["tags"] else [],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def validate_api_key(self, key: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM api_keys WHERE key = ? AND is_active = 1", (key,)
            ).fetchone()
            if row:
                return dict(row)
            return None

    def register_api_key(self, key: str, client_name: str, tier: str = "standard", monthly_quota: int = 1000) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO api_keys (key, client_name, tier, is_active, monthly_quota, created_at)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (key, client_name, tier, monthly_quota, datetime.now(timezone.utc).isoformat())
            )

    def record_api_request(self, key: str, endpoint: str, status_code: int, revenue_usd: float = 0.0) -> None:
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        now_iso = now.isoformat()

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO api_requests (key, endpoint, status_code, revenue_usd, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (key, endpoint, status_code, revenue_usd, now_iso)
            )
            # Update Daily Ledger
            conn.execute(
                """
                INSERT INTO daily_ledger (date, engine_a_revenue, engine_b_revenue, total_revenue, api_requests_count, trades_count, updated_at)
                VALUES (?, ?, 0.0, ?, 1, 0, ?)
                ON CONFLICT(date) DO UPDATE SET
                    engine_a_revenue = engine_a_revenue + excluded.engine_a_revenue,
                    total_revenue = total_revenue + excluded.engine_a_revenue,
                    api_requests_count = api_requests_count + 1,
                    updated_at = excluded.updated_at
                """,
                (today, revenue_usd, revenue_usd, now_iso)
            )

    def record_arbitrage_event(self, event_id: str, market_id: str, question: str,
                               news_source: str, news_headline: str, market_price: float,
                               target_price: float, trade_amount_usd: float, profit_usd: float,
                               simulated: bool, status: str) -> None:
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        now_iso = now.isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO arbitrage_events 
                (id, market_id, question, news_source, news_headline, market_price, target_price, trade_amount_usd, profit_usd, simulated, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id, market_id, question, news_source, news_headline,
                    market_price, target_price, trade_amount_usd, profit_usd,
                    1 if simulated else 0, status, now_iso
                )
            )
            # Update Daily Ledger ONLY if a new arbitrage was actually recorded
            if cursor.rowcount > 0:
                conn.execute(
                    """
                    INSERT INTO daily_ledger (date, engine_a_revenue, engine_b_revenue, total_revenue, api_requests_count, trades_count, updated_at)
                    VALUES (?, 0.0, ?, ?, 0, 1, ?)
                    ON CONFLICT(date) DO UPDATE SET
                        engine_b_revenue = engine_b_revenue + excluded.engine_b_revenue,
                        total_revenue = total_revenue + excluded.engine_b_revenue,
                        trades_count = trades_count + 1,
                        updated_at = excluded.updated_at
                    """,
                    (today, profit_usd, profit_usd, now_iso)
                )

    def get_ledger_for_date(self, date_str: str) -> Dict[str, Any]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM daily_ledger WHERE date = ?", (date_str,)).fetchone()
            if row:
                return dict(row)
            return {
                "date": date_str,
                "engine_a_revenue": 0.0,
                "engine_b_revenue": 0.0,
                "total_revenue": 0.0,
                "api_requests_count": 0,
                "trades_count": 0,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

    def get_all_time_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            ledger_totals = conn.execute(
                """
                SELECT 
                    SUM(engine_a_revenue) as total_a,
                    SUM(engine_b_revenue) as total_b,
                    SUM(total_revenue) as total_all,
                    SUM(api_requests_count) as total_requests,
                    SUM(trades_count) as total_trades
                FROM daily_ledger
                """
            ).fetchone()

            opps_count = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]

            return {
                "total_engine_a_revenue_usd": round(ledger_totals["total_a"] or 0.0, 2),
                "total_engine_b_revenue_usd": round(ledger_totals["total_b"] or 0.0, 2),
                "total_revenue_usd": round(ledger_totals["total_all"] or 0.0, 2),
                "total_api_requests": ledger_totals["total_requests"] or 0,
                "total_arbitrage_trades": ledger_totals["total_trades"] or 0,
                "stored_opportunities": opps_count,
            }
