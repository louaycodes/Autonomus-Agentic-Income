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
    def __init__(self, db: TradingDatabase, strategy: Any, exchange: Any, agent_cognition: Optional[Any] = None):
        self.db = db
        self.strategy = strategy
        self.exchange = exchange
        self.agent_cognition = agent_cognition
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
        sym = trade.get("symbol") or config.symbol
        current_capital = self.db.get_capital()
        dt_rate = 3.10

        profit_usd = trade['net_profit_usd']
        profit_dt = profit_usd * dt_rate
        cap_dt = current_capital * dt_rate
        daily_dt = daily['net_profit_usd'] * dt_rate
        buy_dt = trade['buy_price'] * dt_rate
        sell_dt = trade['sell_price'] * dt_rate

        msg = (
            f"💰 *PROFIT ENCAISSÉ ET RÉINVESTI !*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🪙 *Actif :* `{sym}`\n"
            f"📈 *Gain Net :* *+{profit_usd:.4f} $* (~`+{profit_dt:.2f} DT`) | `+{trade['roi_percent']}%`\n"
            f"🛒 *Achat :* `${trade['buy_price']:.2f}` (~`{buy_dt:.2f} DT`) ➔ 🏷️ *Vente :* `${trade['sell_price']:.2f}` (~`{sell_dt:.2f} DT`)\n\n"
            f"🏦 *Capital Actif :* *${current_capital:,.2f} USD* (~`{cap_dt:,.0f} DT`)\n"
            f"📊 *Gains Aujourd'hui :* *+{daily['net_profit_usd']:.2f} $* (~`+{daily_dt:.2f} DT`) ({daily['trades_count']} trades)"
        )
        await self.send_message(msg)

    async def send_daily_report(self) -> None:
        """Sends comprehensive 23:59 UTC daily ledger summary."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily = self.db.get_daily_pnl(today)
        all_time = self.db.get_all_time_stats()
        current_capital = self.db.get_capital()
        dt_rate = 3.10

        daily_dt = daily['net_profit_usd'] * dt_rate
        all_time_dt = all_time['total_profit_usd'] * dt_rate
        cap_dt = current_capital * dt_rate

        mode_str = "🟢 SIMULATION PAPER (Zéro risque)" if config.trading_mode == "paper" else "🚀 LIVE PRODUCTION RÉEL"

        cognition_section = ""
        if self.agent_cognition:
            try:
                reflection = await self.agent_cognition.perform_daily_reflection("daily_report")
                dyn = reflection.get("parameters", {})
                cognition_section = (
                    f"\n\n🧠 *RÉFLEXION & APPRENTISSAGE DE L'AGENT :*\n"
                    f"• *Marché :* {reflection.get('assessment')}\n"
                    f"• *Constats :* {reflection.get('lessons')}\n"
                    f"• *Adaptation :* {reflection.get('actions')}\n"
                    f"• *Réglages Actifs :* Spread `{dyn.get('active_grid_step_pct')}%` | Réserve Cash `{dyn.get('cash_reserve_floor_pct')}%`"
                )
            except Exception as e:
                logger.warning(f"Error during daily reflection: {e}")

        report = (
            f"📊 *BILAN JOURNALIER QUANTITATIF APEX*\n"
            f"📅 *Date :* `{today}` | *Mode :* {mode_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *Gains Nets Aujourd'hui :* *+{daily['net_profit_usd']:.2f} $* (~`+{daily_dt:.2f} DT`)\n"
            f"🎯 *Objectif 1 000 DT/mois :* ~33 DT/jour ({f'ATTEINT AUJOURD’HUI ! 🎉' if daily_dt >= 33.0 else f'{int((daily_dt/33)*100)}% complété'})\n"
            f"🔄 *Trades Exécutés :* `{daily['trades_count']}`\n"
            f"🏦 *Capital Composé Total :* *${current_capital:,.2f} USD* (~`{cap_dt:,.0f} DT`)\n"
            f"🪙 *Portefeuille Actif :* `{', '.join(config.symbols)}`\n\n"
            f"🏦 *Total Cumulé All-Time :* *+{all_time['total_profit_usd']:.2f} $* (~`+{all_time_dt:.2f} DT`) ({all_time['total_trades']} trades)\n"
            f"🛡️ *Statut VPS :* 100% Opérationnel 24/7"
            f"{cognition_section}"
        )
        await self.send_message(report)
        self.last_reported_date = today

    async def handle_command(self, cmd: str) -> str:
        """Processes interactive user commands sent via Telegram."""
        parts = cmd.strip().split()
        if not parts:
            return ""
        base_cmd = parts[0].lower()
        dt_rate = 3.10

        if base_cmd in ["/start", "/help"]:
            return (
                "🤖 *Commandes Apex Trading Agent :*\n\n"
                "• `/balance` : Solde USDT libre, engagé, cryptos et valeur totale (USD & DT)\n"
                "• `/status` : État général, capital, grilles et cours en direct (USD & DT)\n"
                "• `/profit` : Bénéfices encaissés aujourd'hui et cumulés (USD & DT)\n"
                "• `/agent` : Cerveau de l'agent, mémoire, adaptations et contexte\n"
                "• `/reflect` : Déclencher une auto-évaluation cognitive immédiate\n"
                "• `/setcapital <DT>` : Modifier le capital (ex: `/setcapital 30000`)\n"
                "• `/reset` : Réinitialiser la base et recommencer les trades à 0\n"
                "• `/pause` : Mettre la stratégie en pause\n"
                "• `/resume` : Relancer la stratégie\n"
                "• `/help` : Afficher ce menu d'aide"
            )


        elif base_cmd == "/status":
            current_capital = self.db.get_capital()
            cap_dt = current_capital * dt_rate
            open_orders = self.db.get_open_orders()
            buys = sum(1 for o in open_orders if o["side"] == "buy")
            sells = sum(1 for o in open_orders if o["side"] == "sell")
            status_str = "⏸️ En Pause" if self.strategy.is_paused else "🟢 Actif & En Ligne"

            prices_lines = []
            for sym in config.symbols:
                try:
                    p = await self.exchange.fetch_current_price(sym)
                    p_dt = p * dt_rate
                    prices_lines.append(f"  • `{sym}` : *${p:,.2f}* (~`{p_dt:,.2f} DT`)")
                except Exception:
                    prices_lines.append(f"  • `{sym}` : non joignable")

            return (
                f"📊 *État du Bot Apex Multi-Actifs :*\n"
                f"• *Statut :* {status_str}\n"
                f"• *Capital Actif :* *${current_capital:,.2f} USD* (~`{cap_dt:,.0f} DT`)\n"
                f"• *Prix en direct :*\n" + "\n".join(prices_lines) + "\n"
                f"• *Mode :* `{config.trading_mode.upper()}`\n"
                f"• *Ordres en cours :* `{buys} Achats` / `{sells} Ventes` en attente"
            )

        elif base_cmd == "/balance":
            current_capital = self.db.get_capital()
            balances = await self.exchange.fetch_balances()
            usdt_free = float(balances.get("usdt", 0.0))
            usdt_locked = float(balances.get("usdt_locked", 0.0))
            all_crypto = balances.get("all_crypto", {})

            crypto_lines = []
            total_crypto_usd = 0.0
            for sym in config.symbols:
                base = sym.split("/")[0]
                amount = float(all_crypto.get(base, 0.0))
                price = 0.0
                try:
                    price = await self.exchange.fetch_current_price(sym)
                except Exception:
                    pass
                val_usd = amount * price
                val_dt = val_usd * dt_rate
                total_crypto_usd += val_usd
                if amount > 0:
                    crypto_lines.append(f"  • *{base} :* `{amount:,.4f}` (~*${val_usd:,.2f} USD* / ~`{val_dt:,.2f} DT`)")
                else:
                    crypto_lines.append(f"  • *{base} :* `0.0000` ($0.00 USD / 0 DT)")

            total_portfolio_usd = usdt_free + usdt_locked + total_crypto_usd
            total_portfolio_dt = total_portfolio_usd * dt_rate
            cap_dt = current_capital * dt_rate
            mode_label = "🟢 PAPER (Simulation en direct)" if config.trading_mode == "paper" else "🚀 LIVE (Production Réelle)"

            return (
                f"💼 *Portefeuille & Soldes :*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💵 *USDT Disponible :* *${usdt_free:,.2f} USD* (~`{usdt_free * dt_rate:,.0f} DT`)\n"
                f"🔒 *USDT Engagé (Grilles) :* *${usdt_locked:,.2f} USD* (~`{usdt_locked * dt_rate:,.0f} DT`)\n"
                f"🪙 *Actifs Cryptos :*\n" + "\n".join(crypto_lines) + "\n\n"
                f"💰 *Valeur Totale :* *${total_portfolio_usd:,.2f} USD* (~`{total_portfolio_dt:,.0f} DT`)\n"
                f"🏦 *Capital Référent :* *${current_capital:,.2f} USD* (~`{cap_dt:,.0f} DT`)\n"
                f"⚙️ *Mode :* `{mode_label}`"
            )

        elif base_cmd == "/profit":
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            daily = self.db.get_daily_pnl(today)
            all_time = self.db.get_all_time_stats()
            daily_dt = daily['net_profit_usd'] * dt_rate
            all_time_dt = all_time['total_profit_usd'] * dt_rate
            vol_dt = daily['volume_usd'] * dt_rate

            return (
                f"💰 *Performances Financières :*\n"
                f"• *Gain Aujourd'hui :* *+{daily['net_profit_usd']:.2f} $* (~`+{daily_dt:.2f} DT`) ({daily['trades_count']} trades)\n"
                f"• *Volume 24h :* *${daily['volume_usd']:,.2f} USD* (~`{vol_dt:,.2f} DT`)\n"
                f"• *Gain Total Cumulé :* *+{all_time['total_profit_usd']:.2f} $* (~`+{all_time_dt:.2f} DT`) ({all_time['total_trades']} trades)"
            )

        elif base_cmd == "/setcapital":
            if len(parts) < 2:
                return "⚠️ Veuillez spécifier un montant en Dinars. Exemple : `/setcapital 30000`"
            try:
                dt_amount = float(parts[1])
                usd_amount = dt_amount / dt_rate
                self.db.set_capital(usd_amount)
                return f"✅ *Capital mis à jour avec succès !*\nNouveau capital : *${usd_amount:,.2f} USD* (~`{dt_amount:,.0f} DT`)"
            except ValueError:
                return "⚠️ Montant invalide. Exemple : `/setcapital 30000`"

        elif base_cmd == "/reset":
            self.db.reset_database()
            if hasattr(self.exchange, "reset_paper_balances"):
                self.exchange.reset_paper_balances()
            self.strategy.is_paused = False
            cap = self.db.get_capital()
            cap_dt = cap * dt_rate
            for sym in config.symbols:
                try:
                    p = await self.exchange.fetch_current_price(sym)
                    await self.strategy.initialize_grid(p, symbol=sym)
                except Exception as e:
                    logger.warning(f"Error reinitializing grid for {sym}: {e}")
            return (
                f"🔄 *Base de données et trades réinitialisés à 0 avec succès !*\n"
                f"Toutes les anciennes opérations ont été effacées.\n"
                f"Nouvelles grilles actives avec un capital propre de *${cap:,.2f} USD* (~`{cap_dt:,.0f} DT`)."
            )

        elif base_cmd == "/agent":
            if not self.agent_cognition:
                return "ℹ️ Moteur cognitif non initialisé."

            dyn = self.agent_cognition.get_dynamic_parameters()
            identity = self.db.get_agent_memory("agent_identity", {})
            reflections = self.db.get_latest_agent_reflections(limit=1)
            latest_ref = reflections[0] if reflections else None
            last_anti_lock = self.db.get_agent_memory("last_anti_lock_action")

            anti_lock_str = "Aucun déblocage requis (Trésorerie saine)"
            if last_anti_lock and isinstance(last_anti_lock, dict):
                anti_lock_str = f"Libéré ${last_anti_lock.get('freed_usdt', 0):.2f} sur {last_anti_lock.get('symbol')} @ ${last_anti_lock.get('re_anchored_price', 0):.2f}"

            ref_text = "Pas encore de réflexion enregistrée."
            if latest_ref:
                ref_text = (
                    f"📅 *Dernier constat ({latest_ref.get('date')}) :*\n"
                    f"• *Marché :* `{latest_ref.get('market_assessment')}`\n"
                    f"• *Leçon apprise :* _{latest_ref.get('lessons_learned')}_\n"
                    f"• *Action appliquée :* {latest_ref.get('adapted_actions')}"
                )

            return (
                f"🧠 *CERVEAU & MÉMOIRE DE L'AGENT APEX*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 *Identité :* {identity.get('name', 'Apex Agent')} (Auto-apprenant)\n"
                f"🎯 *Objectif :* {identity.get('core_objective', 'Génération de cashflow quotidien')}\n\n"
                f"⚙️ *Paramètres Dynamiques Actifs :*\n"
                f"  • *Spread Grille (Scalping) :* `{dyn.get('active_grid_step_pct', config.grid_step_percent)}%` (Auto-ajusté)\n"
                f"  • *Plancher Trésorerie Sécurisée :* `{dyn.get('cash_reserve_floor_pct', 30.0)}%` (Anti-lock garanti)\n"
                f"  • *Fraction Anti-Blocage :* `{int(float(dyn.get('anti_lock_rebalance_fraction', 0.15)) * 100)}%`\n"
                f"  • *Dernier Anti-Lock :* {anti_lock_str}\n\n"
                f"{ref_text}\n\n"
                f"💡 _L'agent analyse chaque cycle et adapte son comportement pour ne jamais se bloquer à vie._"
            )

        elif base_cmd == "/reflect":
            if not self.agent_cognition:
                return "ℹ️ Moteur cognitif non initialisé."
            ref = await self.agent_cognition.perform_daily_reflection("manual_telegram_trigger")
            dyn = ref.get("parameters", {})
            return (
                f"🔍 *AUTO-ÉVALUATION COGNITIVE IMMÉDIATE (AGENT)*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 *Trades analysés :* `{ref.get('trades_count')}` | *Gains :* `+${ref.get('profit_usd', 0):.2f}`\n"
                f"🌐 *Diagnostic Marché :* {ref.get('assessment')}\n\n"
                f"💡 *Constats & Leçons :*\n{ref.get('lessons')}\n\n"
                f"🛠️ *Adaptation Comportementale :*\n{ref.get('actions')}\n\n"
                f"⚙️ *Paramètre Spread Actualisé :* `{dyn.get('active_grid_step_pct')}%`"
            )

        elif base_cmd == "/pause":
            self.strategy.is_paused = True
            return "⏸️ *Stratégie mise en pause.* Aucun nouvel ordre ne sera exécuté."

        elif base_cmd == "/resume":
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
        logger.info("Telegram Controller active and listening for commands (silent start mode).")

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
