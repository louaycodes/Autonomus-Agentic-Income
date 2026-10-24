"""Unit tests for AgentCognitionEngine and persistent cognitive memory."""
import pytest
from pathlib import Path
from src.trading.storage import TradingDatabase
from src.trading.exchange import ExchangeAdapter
from src.trading.agent_memory import AgentCognitionEngine
from src.trading.strategy import SpotGridStrategy

@pytest.fixture
def clean_db(tmp_path: Path):
    db_file = tmp_path / "test_agent.db"
    return TradingDatabase(db_file)

@pytest.mark.asyncio
async def test_agent_memory_and_reflection(clean_db):
    exchange = ExchangeAdapter(clean_db)
    agent = AgentCognitionEngine(clean_db, exchange)

    # Test agent identity in memory
    identity = clean_db.get_agent_memory("agent_identity")
    assert identity is not None
    assert "Apex" in identity.get("name", "")

    # Test dynamic parameters
    params = agent.get_dynamic_parameters()
    assert "active_grid_step_pct" in params
    assert params["cash_reserve_floor_pct"] >= 20.0

    # Test performing daily reflection
    ref = await agent.perform_daily_reflection("test_trigger")
    assert ref["id"] is not None
    assert ref["trades_count"] == 0
    assert "Zéro trade" in ref["lessons"]

    # Test retrieving reflections
    latest = clean_db.get_latest_agent_reflections(limit=1)
    assert len(latest) == 1
    assert latest[0]["id"] == ref["id"]

@pytest.mark.asyncio
async def test_strategy_with_agent_cognition(clean_db):
    exchange = ExchangeAdapter(clean_db)
    agent = AgentCognitionEngine(clean_db, exchange)
    strategy = SpotGridStrategy(clean_db, exchange, agent_cognition=agent)

    # Verify strategy uses agent's dynamic step
    dyn_step = agent.get_dynamic_parameters()["active_grid_step_pct"] / 100.0
    assert strategy.current_step_pct == dyn_step
    assert strategy.cash_reserve_floor_pct >= 25.0
