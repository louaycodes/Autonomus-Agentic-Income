import pytest
from pathlib import Path
from src.cluster.storage import Database

@pytest.fixture
def temp_db(tmp_path: Path):
    db_file = tmp_path / "test_cluster.db"
    return Database(db_file)

def test_storage_init_and_wal(temp_db: Database):
    conn = temp_db.get_connection()
    journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    assert journal_mode.lower() == "wal"
    conn.close()

def test_opportunity_save_and_retrieve(temp_db: Database):
    saved = temp_db.save_opportunity(
        opp_id="opp_100",
        title="Appel d'offres Cloud Kubernetes",
        source="boamp",
        category="cloud",
        budget_eur=50000.0,
        deadline="2026-12-01",
        tags=["cloud", "devops"],
        raw_data={"test": True}
    )
    assert saved is True

    # Duplicate insertion must be ignored (idempotent)
    saved_duplicate = temp_db.save_opportunity(
        opp_id="opp_100",
        title="Appel d'offres Cloud Kubernetes",
        source="boamp",
        category="cloud",
        budget_eur=50000.0,
        deadline="2026-12-01",
        tags=["cloud", "devops"],
        raw_data={"test": True}
    )
    assert saved_duplicate is False

    opps = temp_db.get_opportunities(limit=10)
    assert len(opps) == 1
    assert opps[0]["id"] == "opp_100"
    assert opps[0]["budget_eur"] == 50000.0
    assert "cloud" in opps[0]["tags"]

def test_api_keys_and_requests_ledger(temp_db: Database):
    temp_db.register_api_key("test_key_123", client_name="Test Corp", tier="pro")
    client = temp_db.validate_api_key("test_key_123")
    assert client is not None
    assert client["client_name"] == "Test Corp"

    # Invalid key
    assert temp_db.validate_api_key("fake_key") is None

    # Record API request with revenue
    temp_db.record_api_request("test_key_123", "/api/v1/opportunities", 200, revenue_usd=0.02)
    temp_db.record_api_request("test_key_123", "/api/v1/opportunities", 200, revenue_usd=0.02)

    stats = temp_db.get_all_time_stats()
    assert stats["total_engine_a_revenue_usd"] == 0.04
    assert stats["total_api_requests"] == 2

def test_arbitrage_recording(temp_db: Database):
    temp_db.record_arbitrage_event(
        event_id="arb_99",
        market_id="poly_fed",
        question="Will Fed cut rates?",
        news_source="reuters",
        news_headline="Fed cut confirmed",
        market_price=0.85,
        target_price=1.00,
        trade_amount_usd=20.0,
        profit_usd=3.53,
        simulated=True,
        status="executed"
    )

    stats = temp_db.get_all_time_stats()
    assert stats["total_engine_b_revenue_usd"] == 3.53
    assert stats["total_arbitrage_trades"] == 1
