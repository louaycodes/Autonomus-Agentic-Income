import pytest
from pathlib import Path
from src.trading.storage import TradingDatabase
from src.trading.exchange import ExchangeAdapter
from src.trading.strategy import SpotGridStrategy
from src.trading.telegram_bot import TelegramController

@pytest.fixture
def test_bot_setup(tmp_path: Path):
    db = TradingDatabase(tmp_path / "test_tg.db")
    exchange = ExchangeAdapter(db)
    strategy = SpotGridStrategy(db, exchange)
    bot = TelegramController(db, strategy, exchange)
    return bot, strategy

@pytest.mark.asyncio
async def test_telegram_commands(test_bot_setup):
    bot, strategy = test_bot_setup

    help_reply = await bot.handle_command("/help")
    assert "/status" in help_reply
    assert "/balance" in help_reply

    pause_reply = await bot.handle_command("/pause")
    assert strategy.is_paused is True
    assert "pause" in pause_reply.lower()

    resume_reply = await bot.handle_command("/resume")
    assert strategy.is_paused is False
    assert "relancée" in resume_reply.lower()

    unknown_reply = await bot.handle_command("/inconnue")
    assert "inconnue" in unknown_reply.lower()
