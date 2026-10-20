import pytest
from pathlib import Path
from src.trading.storage import TradingDatabase

@pytest.fixture
def temp_db(tmp_path: Path):
    return TradingDatabase(tmp_path / "test_trading.db")

def test_wal_mode_and_init(temp_db: TradingDatabase):
    conn = temp_db.get_connection()
    mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    assert mode.lower() == "wal"
    conn.close()

def test_order_management(temp_db: TradingDatabase):
    temp_db.save_order("ord_1", "buy", 140.0, 0.1, 14.0, "open")
    temp_db.save_order("ord_2", "sell", 150.0, 0.1, 15.0, "open")

    open_buys = temp_db.get_open_orders(side="buy")
    assert len(open_buys) == 1
    assert open_buys[0]["order_id"] == "ord_1"
    assert open_buys[0]["price"] == 140.0

    temp_db.update_order_status("ord_1", "filled")
    open_buys_after = temp_db.get_open_orders(side="buy")
    assert len(open_buys_after) == 0

def test_completed_trade_and_daily_pnl(temp_db: TradingDatabase):
    res = temp_db.record_completed_trade(
        trade_id="tr_101",
        buy_price=140.0,
        sell_price=145.0,
        amount=0.1,
        fee_usd=0.0145
    )
    assert res["net_profit_usd"] > 0
    assert res["roi_percent"] > 0

    stats = temp_db.get_all_time_stats()
    assert stats["total_trades"] == 1
    assert stats["total_profit_usd"] > 0

def test_bot_state(temp_db: TradingDatabase):
    temp_db.set_state("paused", "true")
    assert temp_db.get_state("paused") == "true"
    temp_db.set_state("paused", "false")
    assert temp_db.get_state("paused") == "false"

def test_reset_database(temp_db: TradingDatabase):
    temp_db.save_order("ord_reset", "buy", 100.0, 1.0, 100.0, "open")
    temp_db.record_completed_trade("tr_reset", 100.0, 105.0, 1.0, 0.1)
    assert len(temp_db.get_open_orders()) == 1
    assert temp_db.get_all_time_stats()["total_trades"] == 1

    temp_db.reset_database(initial_capital=5000.0)
    assert len(temp_db.get_open_orders()) == 0
    assert temp_db.get_all_time_stats()["total_trades"] == 0
    assert temp_db.get_capital() == 5000.0
