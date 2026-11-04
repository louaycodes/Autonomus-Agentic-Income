import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from src.dashboard.app import app
import src.dashboard.app as dash_app
from src.trading.storage import TradingDatabase

@pytest.fixture
def test_dash_db(tmp_path: Path, monkeypatch):
    test_db_path = tmp_path / "trading.db"
    db = TradingDatabase(test_db_path)
    db.reset_database(9675.0)

    # Mock fetch_live_prices to return fast static prices
    async def mock_live_prices():
        return {"BTC": 77000.0, "SOL": 93.0, "ETH": 2300.0}

    monkeypatch.setattr(dash_app, "fetch_live_prices", mock_live_prices)
    monkeypatch.setattr(dash_app, "DB_PATH", test_db_path)
    monkeypatch.setattr(dash_app, "DT_RATE", 3.10)
    return db

def test_dashboard_health():
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["currency"] == "DT"
    assert data["rate"] == 3.10

def test_dashboard_status_empty(test_dash_db):
    client = TestClient(app)
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["currency"] == "DT"
    assert "portfolio" in data
    assert data["portfolio"]["total_dt"] > 0
    assert "crypto_assets" in data
    assert len(data["crypto_assets"]) == 3
    assert data["performance"]["total_trades_count"] == 0

def test_dashboard_status_populated(test_dash_db):
    # Insert mock orders and a completed trade
    test_dash_db.save_order("buy_1", "buy", 70000.0, 0.01, 700.0, "open", symbol="BTC/USDT")
    test_dash_db.save_order("sell_1", "sell", 71000.0, 0.01, 710.0, "open", symbol="BTC/USDT")
    test_dash_db.record_completed_trade("trade_test_1", 70000.0, 71000.0, 0.01, 0.5, symbol="BTC/USDT")

    client = TestClient(app)
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["performance"]["total_trades_count"] == 1
    assert data["performance"]["profit_today_dt"] > 0
    assert data["open_orders"]["total_count"] == 2
    assert len(data["recent_trades"]) == 1
    assert data["recent_trades"][0]["symbol"] == "BTC/USDT"

def test_dashboard_missing_db(tmp_path: Path, monkeypatch):
    non_existent = tmp_path / "missing.db"
    monkeypatch.setattr(dash_app, "DB_PATH", non_existent)
    client = TestClient(app)
    resp = client.get("/api/status")
    assert resp.status_code == 503

def test_dashboard_html_serves():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Apex Trader" in resp.text
    assert "Dinar Tunisien (DT)" in resp.text
    assert "DT" in resp.text
