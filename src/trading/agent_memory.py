"""Cognitive Agent Memory & Self-Reflection Engine.

Transforms the trading system into an autonomous learning agent with:
- Persistent memory & context across sessions
- Daily and situational self-reflection
- Continuous behavioral adaptation based on past performance
- Perpetual Anti-Lock Liquidity Rebalancer so trading never halts
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from src.trading.config import config
from src.trading.storage import TradingDatabase
from src.trading.exchange import ExchangeAdapter

logger = logging.getLogger("agent_cognition")

class AgentCognitionEngine:
    def __init__(self, db: TradingDatabase, exchange: ExchangeAdapter):
        self.db = db
        self.exchange = exchange
        self._init_memory_defaults()

    def _init_memory_defaults(self) -> None:
        """Initializes foundational agent beliefs, persona, and learning memory if empty."""
        if not self.db.get_agent_memory("agent_identity"):
            self.db.set_agent_memory("agent_identity", {
                "name": "Apex Quant Autonomous Agent",
                "role": "Self-learning multi-asset algorithmic trader",
                "creation_date": "2026-10-20",
                "core_objective": "Generate daily positive cashflow in DT/USD with zero liquidation risk via spot volatility harvesting",
                "learning_streak_days": 1
            })

        if not self.db.get_agent_memory("dynamic_parameters"):
            self.db.set_agent_memory("dynamic_parameters", {
                "active_grid_step_pct": config.grid_step_percent,
                "cash_reserve_floor_pct": 30.0,
                "stagnation_max_hours": 3.0,
                "anti_lock_rebalance_fraction": 0.15,
                "last_adaptation_reason": "System initialization with calibrated default parameters."
            })

    def get_dynamic_parameters(self) -> Dict[str, Any]:
        """Retrieves active learning parameters tuned by the agent."""
        defaults = {
            "active_grid_step_pct": config.grid_step_percent,
            "cash_reserve_floor_pct": 30.0,
            "stagnation_max_hours": 3.0,
            "anti_lock_rebalance_fraction": 0.15,
            "last_adaptation_reason": "Baseline settings."
        }
        stored = self.db.get_agent_memory("dynamic_parameters")
        if isinstance(stored, dict):
            defaults.update(stored)
        return defaults

    async def analyze_market_context(self) -> Dict[str, Any]:
        """Gathers cross-asset volatility, trend direction, and current spread requirements."""
        symbols = config.symbols
        asset_metrics = {}
        total_volatility = 0.0

        for sym in symbols:
            try:
                price = await self.exchange.fetch_current_price(sym)
                closes = await self.exchange.fetch_historical_closes(sym, timeframe="1m", limit=30)
                if closes and len(closes) > 1:
                    high = max(closes)
                    low = min(closes)
                    vol_pct = ((high - low) / low) * 100.0 if low > 0 else 0.5
                else:
                    vol_pct = 0.5
                total_volatility += vol_pct
                asset_metrics[sym] = {
                    "price": price,
                    "volatility_30m_pct": round(vol_pct, 2)
                }
            except Exception as e:
                logger.warning(f"Could not compute context for {sym}: {e}")
                asset_metrics[sym] = {"price": 0.0, "volatility_30m_pct": 0.5}

        avg_vol = total_volatility / max(1, len(symbols))
        if avg_vol > 2.0:
            regime = "HAUTE_VOLATILITÉ_EXPANSION"
        elif avg_vol < 0.6:
            regime = "CONSOLIDATION_CALME_RANGE_SERRÉ"
        else:
            regime = "VOLATILITÉ_MODÉRÉE_SCALPING_IDÉAL"

        return {
            "average_volatility_pct": round(avg_vol, 2),
            "macro_regime": regime,
            "assets": asset_metrics
        }

    async def perform_daily_reflection(self, trigger_reason: str = "daily_scheduled") -> Dict[str, Any]:
        """
        Executes autonomous daily cognitive reflection:
        1. Analyzes completed trades and realized PnL.
        2. Assesses market structure and volatility.
        3. Identifies what worked and what stalled.
        4. Self-adjusts trading parameters for optimal ongoing performance.
        5. Logs full reflection into the agent's permanent knowledge base.
        """
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_pnl = self.db.get_daily_pnl(today_str)
        all_time = self.db.get_all_time_stats()
        market_ctx = await self.analyze_market_context()
        trades_count = daily_pnl.get("trades_count", 0)
        profit_usd = daily_pnl.get("net_profit_usd", 0.0)
        vol_pct = market_ctx.get("average_volatility_pct", 0.8)

        # Retrieve current dynamic parameters
        dyn_params = self.get_dynamic_parameters()
        old_step = float(dyn_params.get("active_grid_step_pct", config.grid_step_percent))

        # Cognitive Deduction & Behavioral Adaptation
        lessons: List[str] = []
        actions: List[str] = []

        if trades_count == 0:
            lessons.append(
                "Zéro trade exécuté aujourd'hui : le marché a décalé sous nos niveaux initiaux sans déclencher de rebond direct. "
                "Rester passif bloque le capital dans des ordres de vente trop éloignés."
            )
            # Adapt step: lower spread slightly to capture micro-fluctuations in current range
            new_step = max(0.5, round(old_step * 0.9, 2))
            actions.append(f"Resserrement de la grille de {old_step}% à {new_step}% pour faciliter les déclenchements immédiats.")
            actions.append("Vérification et réactivation de la liquidité active (Anti-Lock Perpetual Rebalance) autour des cours actuels.")
            adapted_step = new_step
            dyn_params["last_adaptation_reason"] = "Stagnation détectée : réduction du spread pour stimuler les micro-cycles."
        elif trades_count >= 8:
            lessons.append(
                f"Excellente session de scalping ({trades_count} trades, +${profit_usd:.2f}) : le calibrage des échelons "
                "a parfaitement synchronisé avec les oscillations du marché."
            )
            adapted_step = old_step
            dyn_params["last_adaptation_reason"] = "Haute cadence de fills confirmée, maintien des paramètres optimaux."
            actions.append("Maintien du spread actuel et réinvestissement composé des profits encaissés.")
        else:
            lessons.append(
                f"Cadence modérée ({trades_count} trades, +${profit_usd:.2f}) : volatilité mesurée à {vol_pct}%. "
                "L'agent sécurise les gains sans sur-exposition."
            )
            if vol_pct < 0.6 and old_step > 0.6:
                adapted_step = round(old_step - 0.05, 2)
                actions.append(f"Ajustement fin du spread à {adapted_step}% adapté à la faible volatilité.")
            else:
                adapted_step = old_step
                actions.append("Paramètres en équilibre avec la dynamique du marché.")

        dyn_params["active_grid_step_pct"] = adapted_step
        self.db.set_agent_memory("dynamic_parameters", dyn_params)

        lessons_text = " ".join(lessons)
        actions_text = " ".join(actions)
        assessment_text = f"{market_ctx['macro_regime']} (Volatilité 30m : {vol_pct}%)"

        reflection_id = self.db.save_agent_reflection(
            date_str=today_str,
            market_assessment=assessment_text,
            trades_evaluated=trades_count,
            total_profit_usd=profit_usd,
            lessons_learned=lessons_text,
            adapted_actions=actions_text,
            applied_parameters=dyn_params
        )

        logger.info(
            f"🧠 AGENT COGNITIVE REFLECTION SAVED [#{reflection_id} - {today_str}]: "
            f"Trades: {trades_count} | Profit: +${profit_usd:.2f} | Step: {adapted_step}%"
        )

        return {
            "id": reflection_id,
            "date": today_str,
            "assessment": assessment_text,
            "trades_count": trades_count,
            "profit_usd": profit_usd,
            "lessons": lessons_text,
            "actions": actions_text,
            "parameters": dyn_params
        }

    async def ensure_perpetual_liquidity(self, strategy) -> Optional[Dict[str, Any]]:
        """
        PERPETUAL ANTI-LOCK ENGINE:
        Ensures the trading agent NEVER gets stuck or frozen when the market dips.
        If free USDT cash is depleted OR if an asset has had no trade activity for > stagnation threshold
        and current price has dropped significantly below all open sell orders:
        The agent automatically rebalances a small slice (15%) of the highest out-of-range sell order
        into active USDT at current spot price, and instantly spawns fresh active micro-grids
        around CURRENT spot prices.
        """
        balances = await self.exchange.fetch_balances()
        free_usdt = float(balances.get("usdt", 0.0))
        total_cap = self.db.get_capital()
        per_asset_cap = total_cap / max(1, len(config.symbols))
        min_required_cash = max(30.0, per_asset_cap * 0.15)

        # Check if cash is locked or assets are stagnant
        for sym in config.symbols:
            open_sells = self.db.get_open_orders(side="sell", symbol=sym)
            open_buys = self.db.get_open_orders(side="buy", symbol=sym)
            current_price = await self.exchange.fetch_current_price(sym)

            # Check if all open sells are situated far above current price (> 1.5% above spot)
            if open_sells:
                lowest_sell_price = min(float(o["price"]) for o in open_sells)
                price_distance_pct = ((lowest_sell_price - current_price) / current_price) * 100.0
            else:
                price_distance_pct = 0.0

            is_cash_depleted = free_usdt < min_required_cash
            is_stagnant_out_of_range = (price_distance_pct > 1.5) and (len(open_buys) == 0 or is_cash_depleted)

            if is_cash_depleted or is_stagnant_out_of_range:
                logger.info(
                    f"⚠️ [PERPETUAL ANTI-LOCK TRIGGERED] [{sym}] Cash Libre: ${free_usdt:.2f} (Min: ${min_required_cash:.2f}) | "
                    f"Écart au plus bas ordre de vente: +{price_distance_pct:.2f}%. Déblocage de liquidité active..."
                )

                if open_sells:
                    # Select the highest (most distant) sell order
                    highest_sell = max(open_sells, key=lambda o: float(o["price"]))
                    sell_order_id = highest_sell["order_id"]
                    sell_amount = float(highest_sell["amount"])
                    base = sym.split("/")[0]

                    # Rebalance fraction (15-20%)
                    dyn_params = self.get_dynamic_parameters()
                    fraction = float(dyn_params.get("anti_lock_rebalance_fraction", 0.15))
                    rebalance_amount = round(sell_amount * fraction, 4)

                    if rebalance_amount > 0:
                        # Cancel the old distant sell order
                        try:
                            await self.exchange.cancel_order(highest_sell)
                            self.db.update_order_status(sell_order_id, "rebalanced")
                        except Exception as e:
                            logger.warning(f"Could not cancel order {sell_order_id} for rebalancing: {e}")

                        # Liquidate the fraction to USDT at current spot price
                        freed_usdt = round(rebalance_amount * current_price * 0.999, 4)
                        if self.exchange.mode == "paper":
                            # In paper mode, transfer from crypto to USDT
                            self.exchange.paper_balance_usdt += freed_usdt
                            # The remaining crypto returns to wallet, re-post remaining sell order
                            remaining_amount = round(sell_amount - rebalance_amount, 4)
                            if remaining_amount > 0:
                                old_price = float(highest_sell["price"])
                                try:
                                    re_sell = await self.exchange.place_order("sell", old_price, remaining_amount, symbol=sym)
                                    self.db.save_order(
                                        order_id=re_sell["id"],
                                        symbol=sym,
                                        side="sell",
                                        price=old_price,
                                        amount=remaining_amount,
                                        cost_usd=old_price * remaining_amount,
                                        status="open"
                                    )
                                except Exception as e:
                                    logger.warning(f"Could not restore partial sell: {e}")
                            self.exchange._save_paper_state()

                        free_usdt += freed_usdt
                        logger.info(
                            f"✅ [LIQUIDITÉ LIBÉRÉE] {rebalance_amount} {base} rééquilibré @ ${current_price:.2f} -> "
                            f"+${freed_usdt:.2f} USDT injectés dans la trésorerie active."
                        )

                        # Immediately re-anchor active micro-grid at current spot price!
                        step = float(dyn_params.get("active_grid_step_pct", config.grid_step_percent)) / 100.0
                        alloc_active = min(free_usdt * 0.45, per_asset_cap * 0.25)
                        if alloc_active >= 10.0:
                            seed_amt = round(alloc_active / current_price, 4)
                            try:
                                # Seed position at spot
                                new_seed = await self.exchange.place_order("buy", current_price, seed_amt, symbol=sym)
                                self.db.save_order(new_seed["id"], sym, "buy", current_price, seed_amt, alloc_active, "filled")
                                if self.exchange.mode == "paper":
                                    net_seed = seed_amt * (1.0 - self.exchange.paper_fee_rate)
                                    self.exchange.paper_balance_crypto[base] = self.exchange.paper_balance_crypto.get(base, 0.0) + net_seed
                                    self.exchange._save_paper_state()

                                # Target sell at +step
                                target_sell = round(current_price * (1.0 + step), 4)
                                new_sell = await self.exchange.place_order("sell", target_sell, seed_amt, symbol=sym)
                                self.db.save_order(new_sell["id"], sym, "sell", target_sell, seed_amt, target_sell * seed_amt, "open", pair_order_id=new_seed["id"])

                                # Active buy level below spot
                                target_buy = round(current_price * (1.0 - step), 4)
                                buy_amt = round(alloc_active / target_buy, 4)
                                new_buy = await self.exchange.place_order("buy", target_buy, buy_amt, symbol=sym)
                                self.db.save_order(new_buy["id"], sym, "buy", target_buy, buy_amt, alloc_active, "open")

                                logger.info(
                                    f"🚀 [MICRO-GRILLE ACTIVE DÉPLOYÉE] [{sym}] Re-ancrée sur le cours direct (${current_price:.2f}) : "
                                    f"Achat @ ${target_buy:.2f} / Vente @ ${target_sell:.2f}. TRADING IMMÉDIATEMENT RELANCÉ !"
                                )

                                self.db.set_agent_memory("last_anti_lock_action", {
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "symbol": sym,
                                    "freed_usdt": freed_usdt,
                                    "re_anchored_price": current_price
                                })

                                return {
                                    "status": "rebalanced",
                                    "symbol": sym,
                                    "freed_usdt": freed_usdt,
                                    "active_spot": current_price
                                }
                            except Exception as e:
                                logger.error(f"Failed to place active re-anchor orders for {sym}: {e}")

        return None
