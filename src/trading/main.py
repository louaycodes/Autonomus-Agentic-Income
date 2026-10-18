"""Unified Autonomous Quantitative Trading Agent Orchestrator."""
import asyncio
import logging
import signal
import sys
from src.trading.config import config
from src.trading.storage import TradingDatabase
from src.trading.exchange import ExchangeAdapter
from src.trading.strategy import SpotGridStrategy
from src.trading.telegram_bot import TelegramController

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("apex_main")

async def strategy_loop(strategy: SpotGridStrategy, stop_event: asyncio.Event):
    """Continuous evaluation loop for market orders and grid fills."""
    logger.info(f"Strategy evaluation loop running (tick interval: {config.poll_interval_seconds}s)")
    while not stop_event.is_set():
        try:
            await strategy.evaluate_tick()
        except Exception as e:
            logger.error(f"Strategy tick exception: {e}", exc_info=True)
        await asyncio.sleep(config.poll_interval_seconds)

async def main():
    logger.info("======================================================")
    logger.info("   APEX AUTONOMOUS QUANTITATIVE TRADING AGENT         ")
    logger.info(f"   Symbol: {config.symbol} | Capital: ${config.total_capital_usd}")
    logger.info(f"   Mode: {config.trading_mode.upper()} | Exchange: {config.exchange_name.upper()}")
    logger.info(f"   Database: {config.db_path}")
    logger.info("======================================================")

    # 1. Initialize persistent storage layer
    db = TradingDatabase(config.db_path)

    # 2. Initialize exchange adapter
    exchange = ExchangeAdapter(db)
    await exchange.initialize()

    # 3. Create Telegram bot controller forward-reference
    telegram_bot = None

    async def trade_filled_callback(trade_info):
        if telegram_bot:
            await telegram_bot.notify_trade_filled(trade_info)

    # 4. Instantiate strategy
    strategy = SpotGridStrategy(db, exchange, on_trade_callback=trade_filled_callback)

    # 5. Instantiate Telegram controller
    telegram_bot = TelegramController(db, strategy, exchange)

    # 6. Pre-warm strategy with initial price fetch
    try:
        price = await exchange.fetch_current_price()
        logger.info(f"Market Connection Verified: {config.symbol} = ${price:.2f}")
    except Exception as e:
        logger.error(f"Market pre-warm note: {e}")

    # 7. Setup graceful exit handlers
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handle_exit():
        logger.info("Termination signal received. Gracefully saving state and stopping...")
        stop_event.set()
        telegram_bot.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_exit)
        except NotImplementedError:
            pass

    # 8. Run concurrent 24/7 worker tasks
    tasks = [
        asyncio.create_task(strategy_loop(strategy, stop_event)),
        asyncio.create_task(telegram_bot.start()),
    ]

    logger.info("All trading and monitoring engines operational 24/7.")
    await asyncio.gather(*tasks, return_exceptions=True)
    await exchange.close()
    logger.info("Apex Trading Agent shutdown completed cleanly.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
