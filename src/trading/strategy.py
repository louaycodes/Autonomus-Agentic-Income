"""Quantitative Geometric Spot Grid Trading Strategy with Anti-Crash Trend Guard."""
import asyncio
import logging
import uuid
from typing import List, Dict, Any, Optional, Callable
from src.trading.config import config
from src.trading.storage import TradingDatabase
from src.trading.exchange import ExchangeAdapter
from src.trading.indicators import evaluate_market_regime

logger = logging.getLogger("strategy")

class SpotGridStrategy:
    def __init__(
        self,
        db: TradingDatabase,
        exchange: ExchangeAdapter,
        on_trade_callback: Optional[Callable] = None,
        agent_cognition: Optional[Any] = None
    ):
        self.db = db
        self.exchange = exchange
        self.on_trade_callback = on_trade_callback
        self.agent_cognition = agent_cognition
        self.is_paused = False
        self.symbols = config.symbols
        self.grid_levels = config.grid_levels
        self.step_pct = config.grid_step_percent / 100.0
        self.half_span_pct = config.range_half_span_percent / 100.0

    @property
    def current_step_pct(self) -> float:
        """Dynamically calibrated step percentage learned by the Agent Cognition Engine."""
        if self.agent_cognition:
            dyn = self.agent_cognition.get_dynamic_parameters()
            return float(dyn.get("active_grid_step_pct", config.grid_step_percent)) / 100.0
        return self.step_pct

    @property
    def cash_reserve_floor_pct(self) -> float:
        """Minimum liquidity cash floor reserved to prevent grid lock."""
        if self.agent_cognition:
            dyn = self.agent_cognition.get_dynamic_parameters()
            return float(dyn.get("cash_reserve_floor_pct", 30.0))
        return 30.0


    async def initialize_grid(self, current_price: float, symbol: Optional[str] = None) -> None:
        """Sets up the initial grid orders around current price for a specific asset symbol."""
        sym = symbol or config.symbol
        open_orders = self.db.get_open_orders(symbol=sym)
        if open_orders:
            logger.info(f"Existing grid for {sym} restored from database ({len(open_orders)} active orders).")
            return

        # Fetch current dynamic compounding capital
        total_working_capital = self.db.get_capital()
        per_asset_capital = total_working_capital / max(1, len(self.symbols))

        logger.info(
            f"Initializing fresh Geometric Grid for {sym} around ${current_price:.2f} "
            f"(Allocated Capital: ${per_asset_capital:.2f} / Total: ${total_working_capital:.2f})..."
        )

        # Allocate 65% for grid orders, 35% reserved for perpetual cash buffer floor
        step = self.current_step_pct
        levels_count = max(4, self.grid_levels // 2)
        total_working_alloc = per_asset_capital * 0.65
        alloc_per_level_usd = total_working_alloc / levels_count

        # 1. Active Seed Position: buy 1 level at current market price to immediately hold inventory for upside profit
        seed_amount = round(alloc_per_level_usd / current_price, 4)
        try:
            seed_order = await self.exchange.place_order("buy", current_price, seed_amount, symbol=sym)
            self.db.save_order(
                order_id=seed_order["id"],
                symbol=sym,
                side="buy",
                price=current_price,
                amount=seed_amount,
                cost_usd=alloc_per_level_usd,
                status="filled"
            )
            if self.exchange.mode == "paper":
                base = sym.split("/")[0]
                fee_crypto = seed_amount * self.exchange.paper_fee_rate
                net_crypto = seed_amount - fee_crypto
                self.exchange.paper_balance_crypto[base] = self.exchange.paper_balance_crypto.get(base, 0.0) + net_crypto
                self.exchange._save_paper_state()

            # Immediately place the target SELL order at +step above current price
            target_sell_price = round(current_price * (1.0 + step), 4)
            sell_order = await self.exchange.place_order("sell", target_sell_price, seed_amount, symbol=sym)
            self.db.save_order(
                order_id=sell_order["id"],
                symbol=sym,
                side="sell",
                price=target_sell_price,
                amount=seed_amount,
                cost_usd=target_sell_price * seed_amount,
                status="open",
                pair_order_id=seed_order["id"]
            )
            logger.info(f"[{sym}] Active Seed Position taken: {seed_amount} @ ${current_price:.2f} -> Initial Target [SELL] placed: ${target_sell_price:.2f} (+{round(step * 100, 2)}%)")
        except Exception as e:
            logger.warning(f"[{sym}] Could not place active seed position: {e}")

        # 2. Place remaining buy limit orders below current price (levels 1 to levels_count - 1)
        for i in range(1, levels_count):
            buy_price = round(current_price * (1.0 - (i * step)), 4)
            amount = round(alloc_per_level_usd / buy_price, 4)

            try:
                order = await self.exchange.place_order("buy", buy_price, amount, symbol=sym)
                self.db.save_order(
                    order_id=order["id"],
                    symbol=sym,
                    side="buy",
                    price=buy_price,
                    amount=amount,
                    cost_usd=alloc_per_level_usd,
                    status="open"
                )
                logger.info(f"[{sym}] Grid Level [BUY] placed: {amount} @ ${buy_price:.2f} (${alloc_per_level_usd:.2f})")
            except Exception as e:
                logger.warning(f"[{sym}] Could not place buy grid level {i}: {e}")


    async def evaluate_tick_for_symbol(self, sym: str) -> List[Dict[str, Any]]:
        """Evaluates price and orders for one specific asset symbol."""
        current_price = await self.exchange.fetch_current_price(sym)
        closes_1m = await self.exchange.fetch_historical_closes(sym, timeframe="1m", limit=50)
        regime = evaluate_market_regime(closes_1m)

        # Check if grid needs initial setup for this symbol
        open_orders = self.db.get_open_orders(symbol=sym)
        if not open_orders:
            await self.initialize_grid(current_price, sym)
            open_orders = self.db.get_open_orders(symbol=sym)

        completed_cycles = []

        # Check open orders for fills
        for order in open_orders:
            is_filled = await self.exchange.check_order_fill(order, current_price)
            if not is_filled:
                continue

            order_id = order["order_id"]
            side = order["side"]
            price = float(order["price"])
            amount = float(order["amount"])

            self.db.update_order_status(order_id, "filled")
            logger.info(f"[{sym}] GRID ORDER FILLED [{side.upper()}]: {amount} @ ${price:.2f}")

            step = self.current_step_pct

            if side == "buy":
                # BUY filled -> place corresponding SELL order at higher level (+step)
                target_sell_price = round(price * (1.0 + step), 4)
                try:
                    sell_order = await self.exchange.place_order("sell", target_sell_price, amount, symbol=sym)
                    self.db.save_order(
                        order_id=sell_order["id"],
                        symbol=sym,
                        side="sell",
                        price=target_sell_price,
                        amount=amount,
                        cost_usd=target_sell_price * amount,
                        status="open",
                        pair_order_id=order_id
                    )
                    logger.info(f"[{sym}] Recycled -> Placed [SELL] order: {amount} @ ${target_sell_price:.2f}")
                except Exception as e:
                    logger.error(f"[{sym}] Failed to place paired sell order: {e}")

            elif side == "sell":
                # SELL filled -> PROFIT REALIZED! Record completed trade & compound profit
                buy_price = round(price / (1.0 + step), 4)
                trade_id = f"trade_{uuid.uuid4().hex[:10]}"

                trade_info = self.db.record_completed_trade(
                    trade_id=trade_id,
                    symbol=sym,
                    buy_price=buy_price,
                    sell_price=price,
                    amount=amount,
                    fee_usd=round(price * amount * 0.001, 4)
                )

                new_capital = self.db.get_capital()
                completed_cycles.append(trade_info)
                logger.info(
                    f"💰 PROFIT ENCAISSÉ ET RÉINVESTI [{sym}] ! Trade {trade_id}: "
                    f"+${trade_info['net_profit_usd']:.4f} ({trade_info['roi_percent']}%) | "
                    f"Capital Actif Total: ${new_capital:.2f}"
                )

                # Send Instant Telegram Alert
                if self.on_trade_callback:
                    try:
                        await self.on_trade_callback(trade_info)
                    except Exception as e:
                        logger.error(f"Telegram alert callback failed: {e}")

                # Recycle back to BUY order if confluence score & market regime are safe
                confluence_score = regime.get("confluence_score", 50.0)
                is_confluence_safe = confluence_score >= config.min_confluence_score

                if regime["safe_to_buy"] and is_confluence_safe:
                    target_buy_price = round(price * (1.0 - step), 4)
                    try:
                        alloc = target_buy_price * amount
                        new_buy = await self.exchange.place_order("buy", target_buy_price, amount, symbol=sym)
                        self.db.save_order(
                            order_id=new_buy["id"],
                            symbol=sym,
                            side="buy",
                            price=target_buy_price,
                            amount=amount,
                            cost_usd=alloc,
                            status="open"
                        )
                        logger.info(f"[{sym}] Recycled -> Placed [BUY] order (Confluence: {confluence_score}/100): {amount} @ ${target_buy_price:.2f}")
                    except Exception as e:
                        logger.warning(f"[{sym}] Could not re-seed buy order: {e}")
                else:
                    logger.warning(
                        f"[{sym}] Trend Guard / Confluence Active ({regime['regime']}, score: {confluence_score}/100) — "
                        f"Mise en pause de l'achat pour protéger le capital."
                    )

        # 1. Stale Buy Order Cleanup: Cancel buy orders left far behind by rising prices
        stale_threshold = config.stale_order_max_drop_percent / 100.0
        active_buys = self.db.get_open_orders(side="buy", symbol=sym)
        for b_order in active_buys:
            b_price = float(b_order["price"])
            if current_price > b_price and (current_price - b_price) / current_price > stale_threshold:
                try:
                    await self.exchange.cancel_order(b_order)
                    self.db.update_order_status(b_order["order_id"], "cancelled")
                    logger.info(f"[{sym}] Trailing Grid -> Cancelled stale BUY order @ ${b_price:.2f} (price is now ${current_price:.2f}). Capital recycled.")
                except Exception as e:
                    logger.warning(f"[{sym}] Could not cancel stale order: {e}")

        # 2. Dynamic Trailing Grid: replenish buy levels right underneath current price while respecting cash reserve floor
        refreshed_buys = self.db.get_open_orders(side="buy", symbol=sym)
        confluence_score = regime.get("confluence_score", 50.0)
        target_ladder_levels = max(3, (self.grid_levels // 2) - 1)
        step = self.current_step_pct

        if len(refreshed_buys) < target_ladder_levels and regime["safe_to_buy"] and confluence_score >= config.min_confluence_score:
            total_cap = self.db.get_capital()
            per_sym_cap = total_cap / max(1, len(self.symbols))
            alloc_per_level = (per_sym_cap * 0.65) / max(3, self.grid_levels // 2)
            existing_prices = [float(o["price"]) for o in refreshed_buys]

            balances = await self.exchange.fetch_balances()
            free_usdt = float(balances.get("usdt", 0.0))
            cash_floor = total_cap * (self.cash_reserve_floor_pct / 100.0)

            # Only place new ladder buys if free USDT remains comfortably above reserve floor
            if free_usdt >= (cash_floor + alloc_per_level):
                for lvl in range(1, target_ladder_levels + 1):
                    new_bp = round(current_price * (1.0 - (lvl * step)), 4)
                    already_has_nearby = any(abs(new_bp - ep) / new_bp < (step * 0.4) for ep in existing_prices)
                    if not already_has_nearby and alloc_per_level >= 5.0 and free_usdt >= (cash_floor + alloc_per_level):
                        amt = round(alloc_per_level / new_bp, 4)
                        try:
                            new_b = await self.exchange.place_order("buy", new_bp, amt, symbol=sym)
                            self.db.save_order(
                                order_id=new_b["id"],
                                symbol=sym,
                                side="buy",
                                price=new_bp,
                                amount=amt,
                                cost_usd=alloc_per_level,
                                status="open"
                            )
                            existing_prices.append(new_bp)
                            free_usdt -= alloc_per_level
                            logger.info(f"[{sym}] Trailing Grid -> Placed fresh [BUY] level: {amt} @ ${new_bp:.2f} (Ladder count: {len(existing_prices)})")
                        except Exception as e:
                            logger.debug(f"[{sym}] Trailing buy placement skip: {e}")

        # 3. Dynamic Bullish Follow-Through: if all sell orders were filled on a pump, re-seed active inventory
        open_sells = self.db.get_open_orders(side="sell", symbol=sym)
        if len(open_sells) == 0 and regime["safe_to_buy"] and confluence_score >= config.min_confluence_score:
            total_cap = self.db.get_capital()
            per_sym_cap = total_cap / max(1, len(self.symbols))
            alloc_per_level = (per_sym_cap * 0.65) / max(3, self.grid_levels // 2)
            can_buy = True
            if self.exchange.mode == "paper" and self.exchange.paper_balance_usdt < alloc_per_level:
                can_buy = False

            if can_buy:
                amt = round(alloc_per_level / current_price, 4)
                try:
                    p_order = await self.exchange.place_order("buy", current_price, amt, symbol=sym)
                    self.db.save_order(order_id=p_order["id"], symbol=sym, side="buy", price=current_price, amount=amt, cost_usd=alloc_per_level, status="filled")
                    if self.exchange.mode == "paper":
                        base = sym.split("/")[0]
                        net_crypto = amt * (1.0 - self.exchange.paper_fee_rate)
                        self.exchange.paper_balance_crypto[base] = self.exchange.paper_balance_crypto.get(base, 0.0) + net_crypto
                        self.exchange._save_paper_state()
                    t_sell_p = round(current_price * (1.0 + step), 4)
                    s_order = await self.exchange.place_order("sell", t_sell_p, amt, symbol=sym)
                    self.db.save_order(order_id=s_order["id"], symbol=sym, side="sell", price=t_sell_p, amount=amt, cost_usd=t_sell_p*amt, status="open", pair_order_id=p_order["id"])
                    logger.info(f"[{sym}] Trend Follow-Through -> Re-seeded inventory @ ${current_price:.2f} -> Target [SELL] @ ${t_sell_p:.2f} (+{round(step * 100, 2)}%)")
                except Exception as e:
                    logger.debug(f"[{sym}] Trend follow-through skip: {e}")

        return completed_cycles

    async def evaluate_tick(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Main strategy evaluation cycle executed every tick across configured symbols."""
        if self.is_paused:
            return []

        # Autonomous Anti-Lock Perpetual Liquidity Check
        if self.agent_cognition:
            try:
                await self.agent_cognition.ensure_perpetual_liquidity(self)
            except Exception as e:
                logger.debug(f"Perpetual liquidity verification note: {e}")

        if symbol:
            return await self.evaluate_tick_for_symbol(symbol)

        all_completed = []
        for sym in self.symbols:
            try:
                cycles = await self.evaluate_tick_for_symbol(sym)
                all_completed.extend(cycles)
            except Exception as e:
                logger.error(f"Error evaluating tick for symbol {sym}: {e}", exc_info=True)

        return all_completed

