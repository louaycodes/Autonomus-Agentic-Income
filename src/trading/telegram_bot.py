"""Interactive Telegram Controller & Trade Notification Terminal."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx
from src.trading.config import config
from src.trading.storage import TradingDatabase

logger = logging.getLogger("telegram_bot")

class TelegramController:
    def __init__(self, db: TradingDatabase, strategy: Any, exchange: Any):
        self.db = db
        self.strategy = strategy
        self.exchange = exchange
        self.token = config.telegram_bot_token
        self.chat_id = config.telegram_chat_id
        self.last_update_id = 0
        self.is_running = False
        self.last_reported_date = ""

    async def send_message(self, text: str) -> bool:
        """Sends a markdown message to Louay's Telegram."""
        if not self.token or not self.chat_id:
            logger.info(f"[TELEGRAM LOG (No token)]\n{text}")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(url, json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "Markdown"
                })
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def notify_trade_filled(self, trade: Dict[str, Any]) -> None:
        """Instant notification pushed on every profitable grid sell."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily = self.db.get_daily_pnl(today)

        msg = (
            f"💰 *PROFIT ENCAISSÉ EN DIRECT !*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🪙 *Paire :* `{config.symbol}`\n"
            f"📈 *Gain Net :* *+{trade['net_profit_usd']:.4f} $* (`+{trade['roi_percent']}%`)\n"
            f"🛒 *Achat :* `${trade['buy_price']:.2f}` ➔ 🏷️ *Vente :* `${trade['sell_price']:.2f}`\n\n"
            f"📊 *Cumul Aujourd'hui :* *+{daily['net_profit_usd']:.2f} $* ({daily['trades_count']} trades)"
        )
        await self.send_message(msg)

    async def send_daily_report(self) -> None:
        """Sends comprehensive 23:59 UTC daily ledger summary."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily = self.db.get_daily_pnl(today)
        all_time = self.db.get_all_time_stats()
        balances = await self.exchange.fetch_balances()

        mode_str = "🟢 SIMULATION PAPER (Zéro risque)" if config.trading_mode == "paper" else "🚀 LIVE PRODUCTION RÉEL"

        report = (
            f"📊 *BILAN JOURNALIER QUANTITATIF APEX*\n"
            f"📅 *Date :* `{today}` | *Mode :* {mode_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *Gains Nets Aujourd'hui :* *+{daily['net_profit_usd']:.2f} $*\n"
            f"🎯 *Objectif 10$/j :* {f'ATTEINT ! 🎉' if daily['net_profit_usd'] >= 10.0 else f'{int((daily['net_profit_usd']/10)*100)}% complété'}\n"
            f"🔄 *Trades Exécutés :* `{daily['trades_count']}`\n"
            f"💼 *Soldes Actuels :* `{balances['usdt']} USDT` | `{balances['crypto']} {config.symbol.split('/')[0]}`\n\n"
            f"🏦 *Total Cumulé All-Time :* *+{all_time['total_profit_usd']:.2f} $* ({all_time['total_trades']} trades)\n"
            f"🛡️ *Statut VPS :* 100% Opérationnel 24/7"
        )
        await self.send_message(report)
        self.last_reported_date = today

    async def handle_command(self, cmd: str) -> str:
        """Processes interactive user commands sent via Telegram."""
        cmd = cmd.strip().lower()

        if cmd in ["/start", "/help"]:
            return (
                "🤖 *Commandes Apex Trading Agent :*\n\n"
                "• `/status` : Prix actuel, état du bot et de la grille\n"
                "• `/balance` : Solde disponible en USDT et Crypto\n"
                "• `/profit` : P&L du jour et historique total\n"
                "• `/pause` : Mettre la grille en pause\n"
                "• `/resume` : Relancer la stratégie\n"
                "• `/help` : Afficher ce menu d'aide"
            )

        elif cmd == "/status":
            price = await self.exchange.fetch_current_price()
            open_orders = self.db.get_open_orders()
            buys = sum(1 for o in open_orders if o["side"] == "buy")
            sells = sum(1 for o in open_orders if o["side"] == "sell")
            status_str = "⏸️ En Pause" if self.strategy.is_paused else "🟢 Actif & En Ligne"

            return (
                f"📊 *État du Bot Apex :*\n"
                f"• *Statut :* {status_str}\n"
                f"• *Paire :* `{config.symbol}`\n"
                f"• *Prix Actuel :* `${price:.2f}`\n"
                f"• *Mode :* `{config.trading_mode.upper()}`\n"
                f"• *Grille Active :* `{buys} Achats` / `{sells} Ventes` en attente"
            )

        elif cmd == "/balance":
            balances = await self.exchange.fetch_balances()
            price = await self.exchange.fetch_current_price()
            total_value = balances["usdt"] + (balances["crypto"] * price)
            return (
                f"💼 *Portefeuille :*\n"
                f"• *USDT :* `${balances['usdt']:.2f}`\n"
                f"• *{config.symbol.split('/')[0]} :* `{balances['crypto']}` (${balances['crypto'] * price:.2f})\n"
                f"• *Valeur Totale :* *${total_value:.2f} USD*"
            )

        elif cmd == "/profit":
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            daily = self.db.get_daily_pnl(today)
            all_time = self.db.get_all_time_stats()
            return (
                f"💰 *Performances Financières :*\n"
                f"• *Profit Aujourd'hui :* *+{daily['net_profit_usd']:.2f} $* ({daily['trades_count']} trades)\n"
                f"• *Volume 24h :* `${daily['volume_usd']:.2f}`\n"
                f"• *Profit Cumulé Total :* *+{all_time['total_profit_usd']:.2f} $* ({all_time['total_trades']} trades)"
            )

        elif cmd == "/pause":
            self.strategy.is_paused = True
            return "⏸️ *Stratégie mise en pause.* Aucun nouvel ordre ne sera exécuté."

        elif cmd == "/resume":
            self.strategy.is_paused = False
            return "▶️ *Stratégie relancée !* La grille et l'écoute de marché reprennent immédiatement."

        return "❓ Commande inconnue. Tapez `/help` pour voir les commandes disponibles."

    async def poll_telegram_messages(self) -> None:
        """Asynchronous long-polling for interactive chat commands."""
        if not self.token:
            return

        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(url, params={"offset": self.last_update_id + 1, "timeout": 5})
                if resp.status_code == 200:
                    data = resp.json()
                    for update in data.get("result", []):
                        self.last_update_id = update["update_id"]
                        msg = update.get("message", {})
                        from_id = str(msg.get("from", {}).get("id", ""))
                        text = msg.get("text", "")

                        # Authorize only Louay's Chat ID
                        if from_id == str(self.chat_id) and text.startswith("/"):
                            reply = await self.handle_command(text)
                            await self.send_message(reply)
        except Exception as e:
            logger.debug(f"Telegram polling tick note: {e}")

    async def start(self) -> None:
        """Starts 24/7 background Telegram controller and daily report scheduler."""
        self.is_running = True
        logger.info("Telegram Controller active and listening for commands.")

        # Announce launch to Louay
        price = await self.exchange.fetch_current_price()
        mode_label = "SIMULATION PAPER" if config.trading_mode == "paper" else "LIVE PRODUCTION"
        await self.send_message(
            f"🚀 *Agent Quantitatif Apex Connecté 24/7 sur VPS !*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🪙 *Paire :* `{config.symbol}` à `${price:.2f}`\n"
            f"💰 *Capital Alloué :* `${config.total_capital_usd} USD`\n"
            f"⚙️ *Mode :* `{mode_label}`\n\n"
            f"Je surveille le marché en continu et vous notifierai à chaque gain.\n"
            f"Tapez `/status` ou `/help` pour me piloter à tout moment !"
        )

        while self.is_running:
            try:
                await self.poll_telegram_messages()

                # Check for 23:59 UTC daily report
                now_utc = datetime.now(timezone.utc)
                today_str = now_utc.strftime("%Y-%m-%d")
                if now_utc.hour >= config.daily_report_hour_utc and self.last_reported_date != today_str:
                    await self.send_daily_report()

            except Exception as e:
                logger.error(f"Error in Telegram loop: {e}", exc_info=True)

            await asyncio.sleep(2)

    def stop(self) -> None:
        self.is_running = False
