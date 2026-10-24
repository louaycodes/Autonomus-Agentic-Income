"""Unified Autonomous Quantitative Trading Agent Orchestrator."""
import asyncio
import logging
import signal
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.trading.config import config
from src.trading.storage import TradingDatabase
from src.trading.exchange import ExchangeAdapter
from src.trading.strategy import SpotGridStrategy
from src.trading.telegram_bot import TelegramController
from src.trading.agent_memory import AgentCognitionEngine

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
    # 1. Initialize persistent storage layer
    db = TradingDatabase(config.db_path)
    active_capital = db.get_capital()

    logger.info("======================================================")
    logger.info("   APEX AUTONOMOUS QUANTITATIVE TRADING AGENT         ")
    logger.info(f"   Portfolio: {', '.join(config.symbols)} | Capital: ${active_capital:.2f}")
    logger.info(f"   Mode: {config.trading_mode.upper()} | Exchange: {config.exchange_name.upper()}")
    logger.info(f"   Compounding: {'ON' if config.compound_profits else 'OFF'} | Min Confluence: {config.min_confluence_score}/100")
    logger.info(f"   Database: {config.db_path}")
    logger.info("======================================================")

    # 2. Initialize exchange adapter
    exchange = ExchangeAdapter(db)
    await exchange.initialize()

    # 3. Initialize Agent Cognition & Memory Engine
    agent_cognition = AgentCognitionEngine(db, exchange)

    # 4. Create Telegram bot controller forward-reference
    telegram_bot = None

    async def trade_filled_callback(trade_info):
        if telegram_bot:
            await telegram_bot.notify_trade_filled(trade_info)

    # 5. Instantiate strategy with cognitive engine
    strategy = SpotGridStrategy(db, exchange, on_trade_callback=trade_filled_callback, agent_cognition=agent_cognition)

    # 6. Instantiate Telegram controller with cognitive engine
    telegram_bot = TelegramController(db, strategy, exchange, agent_cognition=agent_cognition)


    # 6. Pre-warm strategy with initial price fetch across portfolio
    for sym in config.symbols:
        try:
            price = await exchange.fetch_current_price(sym)
            logger.info(f"Market Connection Verified: {sym} = ${price:.2f}")
        except Exception as e:
            logger.error(f"Market pre-warm note for {sym}: {e}")

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
