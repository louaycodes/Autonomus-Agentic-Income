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
    assert len(open_sells) >= 1
    assert any(s["price"] > target_buy["price"] for s in open_sells)

@pytest.mark.asyncio
async def test_stop_loss_trigger(test_setup):
    db, exchange, strategy = test_setup
    step = strategy.current_step_pct
    entry_buy = round(100.0 / (1.0 + step), 4)
    amount = 1.0
    db.save_order("sell_pos_1", "sell", 100.0, amount, 100.0 * amount, "open", symbol="SOL/USDT")
    exchange.paper_balance_crypto["SOL"] = 1.0
    exchange.paper_balance_usdt = 50.0
    exchange._save_paper_state()

    # Price plunging 6% below entry_buy (exceeding 4.0% stop-loss threshold)
    plunge_price = round(entry_buy * 0.94, 2)
    async def mock_price(sym=None):
        return plunge_price
    async def mock_closes(sym=None, timeframe="1m", limit=50):
        return [plunge_price] * limit

    exchange.fetch_current_price = mock_price
    exchange.fetch_historical_closes = mock_closes

    cycles = await strategy.evaluate_tick_for_symbol("SOL/USDT")
    assert len(cycles) >= 1
    stop_trade = [c for c in cycles if c["net_profit_usd"] < 0][0]
    assert stop_trade["sell_price"] == plunge_price
    assert stop_trade["net_profit_usd"] < 0

    # Sell order was closed by stop-loss
    open_sells = db.get_open_orders(side="sell", symbol="SOL/USDT")
    assert not any(s["order_id"] == "sell_pos_1" for s in open_sells)
    # Recovered USDT back into wallet
    assert exchange.paper_balance_usdt > 50.0
