import pytest
from pathlib import Path
from src.cluster.storage import Database
from src.cluster.engine_b_arbitrage import ArbitrageEngine

@pytest.mark.asyncio
async def test_arbitrage_evaluation(tmp_path: Path):
    db_file = tmp_path / "test_arb.db"
    db = Database(db_file)
    engine = ArbitrageEngine(db)

    trades = await engine.evaluate_and_execute_arbitrage()
    assert len(trades) > 0

    first_trade = trades[0]
    assert first_trade["profit_usd"] > 0
    assert first_trade["spread"] >= 8.0 # min 8% threshold

    # Verify recorded in DB
    stats = db.get_all_time_stats()
    assert stats["total_arbitrage_trades"] == len(trades)
    assert stats["total_engine_b_revenue_usd"] > 0
