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
    def __init__(self, db: TradingDatabase, exchange: ExchangeAdapter, on_trade_callback: Optional[Callable] = None):
        self.db = db
        self.exchange = exchange
        self.on_trade_callback = on_trade_callback
        self.is_paused = False
        self.grid_levels = config.grid_levels
        self.step_pct = config.grid_step_percent / 100.0
        self.half_span_pct = config.range_half_span_percent / 100.0

    async def initialize_grid(self, current_price: float) -> None:
        """Sets up the initial grid orders around current price if none are open."""
        open_orders = self.db.get_open_orders()
        if open_orders:
            logger.info(f"Existing grid restored from database ({len(open_orders)} active orders).")
            return

        logger.info(f"Initializing fresh Geometric Spot Grid around ${current_price:.2f}...")

        # Calculate allocation per level ($100 divided into levels)
        levels_count = max(4, self.grid_levels // 2)
        total_buy_capital = config.total_capital_usd * 0.75  # 75% for buy orders, 25% cash buffer
        alloc_per_level_usd = total_buy_capital / levels_count

        # Place buy orders below current price
        for i in range(1, levels_count + 1):
            buy_price = round(current_price * (1.0 - (i * self.step_pct)), 4)
            amount = round(alloc_per_level_usd / buy_price, 4)

            try:
                order = await self.exchange.place_order("buy", buy_price, amount)
                self.db.save_order(
                    order_id=order["id"],
                    side="buy",
                    price=buy_price,
                    amount=amount,
                    cost_usd=alloc_per_level_usd,
                    status="open"
                )
                logger.info(f"Grid Level [BUY] placed: {amount} @ ${buy_price:.2f} (${alloc_per_level_usd:.2f})")
            except Exception as e:
                logger.warning(f"Could not place buy grid level {i}: {e}")

    async def evaluate_tick(self) -> List[Dict[str, Any]]:
        """Main strategy evaluation cycle executed every tick."""
        if self.is_paused:
            return []

        current_price = await self.exchange.fetch_current_price()
        closes = await self.exchange.fetch_historical_closes(limit=50)
        regime = evaluate_market_regime(closes)

        # Check if grid needs initial setup
        open_orders = self.db.get_open_orders()
        if not open_orders:
            await self.initialize_grid(current_price)
            open_orders = self.db.get_open_orders()

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
            logger.info(f"GRID ORDER FILLED [{side.upper()}]: {amount} @ ${price:.2f}")

            if side == "buy":
                # BUY filled -> place corresponding SELL order at higher level
                target_sell_price = round(price * (1.0 + self.step_pct), 4)
                try:
                    sell_order = await self.exchange.place_order("sell", target_sell_price, amount)
                    self.db.save_order(
                        order_id=sell_order["id"],
                        side="sell",
                        price=target_sell_price,
                        amount=amount,
                        cost_usd=target_sell_price * amount,
                        status="open",
                        pair_order_id=order_id
                    )
                    logger.info(f"Recycled -> Placed [SELL] order: {amount} @ ${target_sell_price:.2f}")
                except Exception as e:
                    logger.error(f"Failed to place paired sell order: {e}")

            elif side == "sell":
                # SELL filled -> PROFIT REALIZED! Record completed trade
                pair_order_id = order.get("pair_order_id")
                # Deduce original buy price (price / (1 + step_pct))
                buy_price = round(price / (1.0 + self.step_pct), 4)
                trade_id = f"trade_{uuid.uuid4().hex[:10]}"

                trade_info = self.db.record_completed_trade(
                    trade_id=trade_id,
                    buy_price=buy_price,
                    sell_price=price,
                    amount=amount,
                    fee_usd=round(price * amount * 0.001, 4)
                )

                completed_cycles.append(trade_info)
                logger.info(
                    f"💰 PROFIT ENCAISSÉ ! Trade {trade_id}: "
                    f"+${trade_info['net_profit_usd']:.4f} ({trade_info['roi_percent']}%) | "
                    f"Acheté: ${buy_price:.2f} -> Vendu: ${price:.2f}"
                )

                # Send Instant Telegram Alert
                if self.on_trade_callback:
                    try:
                        await self.on_trade_callback(trade_info)
                    except Exception as e:
                        logger.error(f"Telegram alert callback failed: {e}")

                # Recycle back to BUY order if market regime is safe (Trend Guard)
                if regime["safe_to_buy"]:
                    target_buy_price = round(price * (1.0 - self.step_pct), 4)
                    try:
                        alloc = target_buy_price * amount
                        new_buy = await self.exchange.place_order("buy", target_buy_price, amount)
                        self.db.save_order(
                            order_id=new_buy["id"],
                            side="buy",
                            price=target_buy_price,
                            amount=amount,
                            cost_usd=alloc,
                            status="open"
                        )
                        logger.info(f"Recycled -> Placed [BUY] order: {amount} @ ${target_buy_price:.2f}")
                    except Exception as e:
                        logger.warning(f"Could not re-seed buy order: {e}")
                else:
                    logger.warning(f"Trend Guard Active ({regime['regime']}) — Pausing buy re-seed to protect capital.")

        return completed_cycles
