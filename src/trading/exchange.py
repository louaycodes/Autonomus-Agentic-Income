"""Unified Exchange Adapter — Supports Live CCXT Exchanges and Live-Ticker Paper Simulator."""
import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
import ccxt.async_support as ccxt_async
from src.trading.config import config
from src.trading.storage import TradingDatabase

logger = logging.getLogger("exchange")

class ExchangeAdapter:
    def __init__(self, db: TradingDatabase):
        self.db = db
        self.mode = config.trading_mode
        self.exchange_id = config.exchange_name
        self.symbol = config.symbol
        self.client: Optional[Any] = None

        # Virtual Paper Wallet (starts with user's configured capital, default $100)
        self.paper_balance_usdt = config.total_capital_usd
        self.paper_balance_crypto = 0.0
        self.paper_fee_rate = 0.001  # Standard 0.1% spot maker/taker fee

    async def initialize(self) -> None:
        """Initializes async CCXT exchange driver."""
        exchange_class = getattr(ccxt_async, self.exchange_id, ccxt_async.binance)
        
        exchange_params: Dict[str, Any] = {
            "enableRateLimit": True,
            "timeout": 15000,
        }

        if self.mode == "live":
            if not config.exchange_api_key or not config.exchange_api_secret:
                raise ValueError("Live trading mode requires EXCHANGE_API_KEY and EXCHANGE_API_SECRET in .env")
            exchange_params["apiKey"] = config.exchange_api_key
            exchange_params["secret"] = config.exchange_api_secret
            if config.exchange_password:
                exchange_params["password"] = config.exchange_password

        self.client = exchange_class(exchange_params)
        logger.info(f"Exchange adapter initialized for {self.exchange_id} (Mode: {self.mode.upper()})")

    async def fetch_current_price(self) -> float:
        """Fetches the real-time ticker price from the exchange."""
        try:
            ticker = await self.client.fetch_ticker(self.symbol)
            return float(ticker["last"])
        except Exception as e:
            logger.warning(f"Failed to fetch live ticker via CCXT ({e}); using fallback price check.")
            # Resilient public API check (Binance direct public endpoint)
            import httpx
            base_sym = self.symbol.replace("/", "")
            async with httpx.AsyncClient(timeout=5.0) as http:
                resp = await http.get(f"https://api.binance.com/api/v3/ticker/price?symbol={base_sym}")
                if resp.status_code == 200:
                    return float(resp.json()["price"])
            raise

    async def fetch_historical_closes(self, limit: int = 50) -> List[float]:
        """Fetches recent 1m/5m candle closing prices for technical analysis."""
        try:
            ohlcv = await self.client.fetch_ohlcv(self.symbol, timeframe="1m", limit=limit)
            return [candle[4] for candle in ohlcv]
        except Exception as e:
            logger.warning(f"Could not fetch OHLCV candles ({e}); constructing price series.")
            price = await self.fetch_current_price()
            return [price * (1 + (i * 0.0005)) for i in range(-limit, 0)]

    async def fetch_balances(self) -> Dict[str, float]:
        """Returns quote (USDT) and base (e.g. SOL) balances."""
        if self.mode == "paper":
            return {
                "usdt": round(self.paper_balance_usdt, 2),
                "crypto": round(self.paper_balance_crypto, 4)
            }
        
        balance_data = await self.client.fetch_balance()
        base, quote = self.symbol.split("/")
        return {
            "usdt": float(balance_data.get("free", {}).get(quote, 0.0)),
            "crypto": float(balance_data.get("free", {}).get(base, 0.0))
        }

    async def place_order(self, side: str, price: float, amount: float) -> Dict[str, Any]:
        """Places a limit order (simulated in paper mode or sent to exchange in live mode)."""
        order_cost = price * amount

        if self.mode == "paper":
            order_id = f"paper_{side}_{uuid.uuid4().hex[:8]}"
            if side == "buy":
                if self.paper_balance_usdt >= order_cost:
                    self.paper_balance_usdt -= order_cost
                else:
                    raise ValueError(f"Insufficient simulated USDT balance: {self.paper_balance_usdt} < {order_cost}")
            elif side == "sell":
                if self.paper_balance_crypto >= amount:
                    self.paper_balance_crypto -= amount

            return {
                "id": order_id,
                "side": side,
                "price": price,
                "amount": amount,
                "cost": order_cost,
                "status": "open"
            }

        # Live exchange order execution
        live_order = await self.client.create_limit_order(self.symbol, side, amount, price)
        return {
            "id": live_order["id"],
            "side": side,
            "price": float(live_order.get("price", price)),
            "amount": float(live_order.get("amount", amount)),
            "cost": float(live_order.get("cost", order_cost)),
            "status": live_order.get("status", "open")
        }

    async def check_order_fill(self, order: Dict[str, Any], current_price: float) -> bool:
        """
        Determines if an open limit order has been filled.
        In paper mode: checks if live price has crossed the limit order price.
        In live mode: queries exchange API for order status.
        """
        side = order["side"]
        target_price = float(order["price"])

        if self.mode == "paper":
            # Buy fill: current price dipped to or below target buy price
            if side == "buy" and current_price <= target_price:
                # Credit crypto to wallet minus fee
                fee_crypto = order["amount"] * self.paper_fee_rate
                self.paper_balance_crypto += (order["amount"] - fee_crypto)
                return True
            # Sell fill: current price rose to or above target sell price
            elif side == "sell" and current_price >= target_price:
                # Credit USDT to wallet minus fee
                gross_usdt = order["amount"] * target_price
                fee_usdt = gross_usdt * self.paper_fee_rate
                self.paper_balance_usdt += (gross_usdt - fee_usdt)
                return True
            return False

        # Live mode fill check
        order_status = await self.client.fetch_order(order["order_id"], self.symbol)
        return order_status["status"] == "closed"

    async def close(self) -> None:
        if self.client:
            await self.client.close()
