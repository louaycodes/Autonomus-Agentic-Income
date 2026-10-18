"""Unified Autonomous Income Cluster Orchestrator."""
import asyncio
import logging
import signal
import sys
import uvicorn
from src.cluster.config import config
from src.cluster.storage import Database
from src.cluster.engine_a_scout import ScoutAgent
from src.cluster.engine_a_gateway import app, db
from src.cluster.engine_b_arbitrage import ArbitrageEngine
from src.cluster.sentinel import SentinelWatchdog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("cluster_main")

async def run_server(server: uvicorn.Server):
    await server.serve()

async def main():
    logger.info("======================================================")
    logger.info("   AUTONOMOUS AGENTIC INCOME CLUSTER — VPS 24/7       ")
    logger.info(f"   Mode: {'SIMULATION (DRY-RUN)' if config.simulation_mode else 'LIVE PRODUCTION'}")
    logger.info(f"   Database: {config.db_path}")
    logger.info("======================================================")

    # Initialize micro-services
    scout = ScoutAgent(db)
    arbitrage = ArbitrageEngine(db)
    sentinel = SentinelWatchdog(db)

    # Pre-warm scout and arbitrage with one immediate cycle
    logger.info("Pre-warming cluster agents...")
    try:
        await scout.run_cycle()
        await arbitrage.evaluate_and_execute_arbitrage()
    except Exception as e:
        logger.warning(f"Initial warm-up cycle notice: {e}")

    # Configure FastAPI server
    uvicorn_config = uvicorn.Config(
        app=app,
        host=config.api_host,
        port=config.api_port,
        log_level="info",
        access_log=False
    )
    server = uvicorn.Server(uvicorn_config)

    # Handle graceful termination signals
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handle_exit():
        logger.info("Termination signal received. Shutting down cluster...")
        scout.stop()
        arbitrage.stop()
        sentinel.stop()
        server.should_exit = True
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_exit)
        except NotImplementedError:
            # Windows fallback
            pass

    # Launch all concurrent asynchronous tasks
    tasks = [
        asyncio.create_task(run_server(server)),
        asyncio.create_task(scout.start()),
        asyncio.create_task(arbitrage.start()),
        asyncio.create_task(sentinel.start()),
    ]

    logger.info(f"Cluster Gateway online at http://{config.api_host}:{config.api_port}")
    logger.info("All 24/7 autonomous agents are operational.")

    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Cluster shutdown completed cleanly.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
