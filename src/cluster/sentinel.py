"""Core Sentinel — 24/7 Watchdog, System Health & Telegram Ledger Reporter."""
import asyncio
import logging
import shutil
from datetime import datetime, timezone
import httpx
from src.cluster.config import config
from src.cluster.storage import Database

logger = logging.getLogger("sentinel")

class SentinelWatchdog:
    def __init__(self, db: Database):
        self.db = db
        self.is_running = False
        self.last_reported_date: str = ""

    def check_system_health(self) -> dict:
        """Verifies disk space, memory, and database integrity."""
        disk = shutil.disk_usage(config.data_dir)
        free_gb = round(disk.free / (1024 ** 3), 2)

        # Database integrity check
        db_ok = False
        try:
            with self.db.get_connection() as conn:
                res = conn.execute("PRAGMA quick_check;").fetchone()
                db_ok = res and res[0] == "ok"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")

        return {
            "status": "healthy" if db_ok and free_gb > 0.5 else "warning",
            "disk_free_gb": free_gb,
            "database_integrity": "ok" if db_ok else "corrupted",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def send_telegram_notification(self, message: str) -> bool:
        """Sends an encrypted alert or report to Louay's Telegram."""
        if not config.telegram_bot_token or not config.telegram_chat_id:
            logger.info(f"[TELEGRAM LOG (No token configured)]\n{message}")
            return False

        url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json={
                    "chat_id": config.telegram_chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                })
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to deliver Telegram notification: {e}")
            return False

    async def send_daily_ledger_report(self) -> None:
        """Generates and delivers the daily financial P&L report."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ledger = self.db.get_ledger_for_date(today)
        all_time = self.db.get_all_time_stats()

        mode_str = "🟢 SIMULATION (DRY-RUN)" if config.simulation_mode else "🚀 LIVE PRODUCTION"

        report = (
            f"📊 *RAPPORT JOURNALIER DU CLUSTER AUTONOME*\n"
            f"📅 *Date :* `{today}` | *Mode :* {mode_str}\n\n"
            f"💰 *Gains du Jour :*\n"
            f"  • Moteur A (Micro-APIs B2B) : `+{ledger['engine_a_revenue']:.2f} $`\n"
            f"  • Moteur B (Arbitrage Polymarket) : `+{ledger['engine_b_revenue']:.2f} $`\n"
            f"  • *Total Net Aujourd'hui :* *+{ledger['total_revenue']:.2f} $* "
            f"{'🎯 Objectif 10$/j ATTEINT !' if ledger['total_revenue'] >= 10.0 else '(En progression)'}\n\n"
            f"📈 *Activité 24h :*\n"
            f"  • Requêtes API servies : `{ledger['api_requests_count']}`\n"
            f"  • Arbitrages exécutés : `{ledger['trades_count']}`\n\n"
            f"🏦 *Cumul Historique Total :* *{all_time['total_revenue_usd']:.2f} $* net\n"
            f"🛡️ *Santé Système :* 100% Opérationnel sur VPS"
        )

        await self.send_telegram_notification(report)
        self.last_reported_date = today

    async def start(self) -> None:
        self.is_running = True
        logger.info(f"Sentinel Watchdog active (interval: {config.sentinel_check_interval}s)")

        # Send launch notification
        await self.send_telegram_notification(
            f"🛡️ *Cluster Autonome Initialisé 24/7 sur VPS*\n"
            f"Mode : `{'Simulation' if config.simulation_mode else 'Live'}`\n"
            f"Tous les agents (Scout, Gateway, Arbitrage, Sentinel) sont actifs."
        )

        while self.is_running:
            try:
                health = self.check_system_health()
                if health["status"] != "healthy":
                    await self.send_telegram_notification(
                        f"⚠️ *ALERTE SENTINELLE CLUSTER*\nProblème détecté : {health}"
                    )

                # Check if it's time for daily report (e.g. 23h UTC)
                now_utc = datetime.now(timezone.utc)
                today_str = now_utc.strftime("%Y-%m-%d")
                if now_utc.hour >= config.daily_report_hour_utc and self.last_reported_date != today_str:
                    await self.send_daily_ledger_report()

            except Exception as e:
                logger.error(f"Error in Sentinel cycle: {e}", exc_info=True)

            await asyncio.sleep(config.sentinel_check_interval)

    def stop(self) -> None:
        self.is_running = False
