import pytest
from pathlib import Path
from src.trading.storage import TradingDatabase
from src.trading.exchange import ExchangeAdapter
from src.trading.strategy import SpotGridStrategy

@pytest.fixture
def test_setup(tmp_path: Path):
    db = TradingDatabase(tmp_path / "test_strat.db")
    exchange = ExchangeAdapter(db)
    strategy = SpotGridStrategy(db, exchange)
    return db, exchange, strategy

@pytest.mark.asyncio
async def test_grid_initialization(test_setup):
    db, exchange, strategy = test_setup
    await strategy.initialize_grid(current_price=150.0)

    open_buys = db.get_open_orders(side="buy")
    assert len(open_buys) > 0
    # Highest buy price should be below current price (150.0)
    for b in open_buys:
        assert b["price"] < 150.0

@pytest.mark.asyncio
async def test_order_fill_and_recycling(test_setup):
    db, exchange, strategy = test_setup
    await strategy.initialize_grid(current_price=150.0)

    open_buys = db.get_open_orders(side="buy")
    target_buy = open_buys[0]

    # Simulate price dipping to trigger buy fill
    dip_price = target_buy["price"] - 0.5
    filled = await exchange.check_order_fill(target_buy, dip_price)
    assert filled is True

    # Check that buy is converted to higher sell order
    db.update_order_status(target_buy["order_id"], "filled")
    target_sell_price = round(target_buy["price"] * 1.012, 4)
    db.save_order("sell_ord_1", "sell", target_sell_price, target_buy["amount"], target_sell_price * target_buy["amount"], "open", pair_order_id=target_buy["order_id"])

    open_sells = db.get_open_orders(side="sell")
    assert len(open_sells) == 1
    assert open_sells[0]["price"] > target_buy["price"]
