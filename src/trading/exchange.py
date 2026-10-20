import asyncio
import json
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

        # Virtual Paper Wallet with persistent DB state
        stored_usdt = self.db.get_state("paper_balance_usdt")
        self.paper_balance_usdt = float(stored_usdt) if stored_usdt is not None else float(config.total_capital_usd)

        stored_crypto = self.db.get_state("paper_balance_crypto")
        if stored_crypto:
            try:
                self.paper_balance_crypto = json.loads(stored_crypto)
            except Exception:
                self.paper_balance_crypto = {s.split("/")[0]: 0.0 for s in config.symbols}
        else:
            self.paper_balance_crypto = {s.split("/")[0]: 0.0 for s in config.symbols}

        self.paper_fee_rate = 0.001  # Standard 0.1% spot maker/taker fee
        self._save_paper_state()

    def _save_paper_state(self) -> None:
        """Persists simulated wallet to SQLite state table."""
        if self.mode == "paper":
            self.db.set_state("paper_balance_usdt", round(self.paper_balance_usdt, 4))
            self.db.set_state("paper_balance_crypto", json.dumps(self.paper_balance_crypto))

    def reset_paper_balances(self) -> None:
        """Resets simulated wallet to initial total capital and zero crypto."""
        self.paper_balance_usdt = float(config.total_capital_usd)
        self.paper_balance_crypto = {s.split("/")[0]: 0.0 for s in config.symbols}
        self._save_paper_state()

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

    async def fetch_current_price(self, symbol: Optional[str] = None) -> float:
        """Fetches the real-time ticker price from the exchange for a given symbol."""
        sym = symbol or self.symbol
        try:
            ticker = await self.client.fetch_ticker(sym)
            return float(ticker["last"])
        except Exception as e:
            logger.warning(f"Failed to fetch live ticker via CCXT for {sym} ({e}); using fallback public API.")
            # Resilient public API check (Binance direct public endpoint)
            import httpx
            base_sym = sym.replace("/", "")
            async with httpx.AsyncClient(timeout=5.0) as http:
                resp = await http.get(f"https://api.binance.com/api/v3/ticker/price?symbol={base_sym}")
                if resp.status_code == 200:
                    return float(resp.json()["price"])
            raise

    async def fetch_historical_closes(self, symbol: Optional[str] = None, timeframe: str = "1m", limit: int = 50) -> List[float]:
        """Fetches recent candle closing prices for technical analysis on given timeframe."""
        sym = symbol or self.symbol
        try:
            ohlcv = await self.client.fetch_ohlcv(sym, timeframe=timeframe, limit=limit)
            return [candle[4] for candle in ohlcv]
        except Exception as e:
            logger.warning(f"Could not fetch OHLCV candles for {sym} ({e}); constructing price series.")
            price = await self.fetch_current_price(sym)
            return [price * (1 + (i * 0.0005)) for i in range(-limit, 0)]

    async def fetch_balances(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Returns quote (USDT), locked funds, and all base asset balances."""
        if self.mode == "paper":
            open_buys = self.db.get_open_orders(side="buy")
            locked_usdt = sum(float(o.get("cost_usd", 0.0)) for o in open_buys)
            crypto_dict: Dict[str, float] = {}
            if isinstance(self.paper_balance_crypto, dict):
                crypto_dict = {k: float(v) for k, v in self.paper_balance_crypto.items()}
            else:
                base = (symbol or self.symbol).split("/")[0]
                crypto_dict = {base: float(self.paper_balance_crypto)}

            base_sym = (symbol or self.symbol).split("/")[0]
            return {
                "usdt": round(self.paper_balance_usdt, 2),
                "usdt_locked": round(locked_usdt, 2),
                "crypto": round(crypto_dict.get(base_sym, 0.0), 4),
                "all_crypto": crypto_dict
            }
        
        balance_data = await self.client.fetch_balance()
        sym = symbol or self.symbol
        base, quote = sym.split("/")
        all_crypto: Dict[str, float] = {}
        for s in config.symbols:
            b = s.split("/")[0]
            all_crypto[b] = float(balance_data.get("free", {}).get(b, 0.0))

        return {
            "usdt": float(balance_data.get("free", {}).get(quote, 0.0)),
            "usdt_locked": float(balance_data.get("used", {}).get(quote, 0.0)),
            "crypto": float(balance_data.get("free", {}).get(base, 0.0)),
            "all_crypto": all_crypto
        }

    async def place_order(self, side: str, price: float, amount: float, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Places a limit order (simulated in paper mode or sent to exchange in live mode)."""
        sym = symbol or self.symbol
        order_cost = price * amount
        base = sym.split("/")[0]

        if not isinstance(self.paper_balance_crypto, dict):
            self.paper_balance_crypto = {self.symbol.split("/")[0]: float(self.paper_balance_crypto)}

        if self.mode == "paper":
            order_id = f"paper_{side}_{uuid.uuid4().hex[:8]}"
            if side == "buy":
                if self.paper_balance_usdt >= order_cost:
                    self.paper_balance_usdt -= order_cost
                    self._save_paper_state()
                else:
                    raise ValueError(f"Insufficient simulated USDT balance: {self.paper_balance_usdt} < {order_cost}")
            elif side == "sell":
                curr_crypto = self.paper_balance_crypto.get(base, 0.0)
                if curr_crypto >= amount:
                    self.paper_balance_crypto[base] = curr_crypto - amount
                    self._save_paper_state()

            return {
                "id": order_id,
                "symbol": sym,
                "side": side,
                "price": price,
                "amount": amount,
                "cost": order_cost,
                "status": "open"
            }

        # Live exchange order execution
        live_order = await self.client.create_limit_order(sym, side, amount, price)
        return {
            "id": live_order["id"],
            "symbol": sym,
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
        sym = order.get("symbol") or self.symbol
        base = sym.split("/")[0]

        if not isinstance(self.paper_balance_crypto, dict):
            self.paper_balance_crypto = {self.symbol.split("/")[0]: float(self.paper_balance_crypto)}

        if self.mode == "paper":
            # Buy fill: current price dipped to or below target buy price
            if side == "buy" and current_price <= target_price:
                # Credit crypto to wallet minus fee
                fee_crypto = order["amount"] * self.paper_fee_rate
                net_crypto = order["amount"] - fee_crypto
                self.paper_balance_crypto[base] = self.paper_balance_crypto.get(base, 0.0) + net_crypto
                self._save_paper_state()
                return True
            # Sell fill: current price rose to or above target sell price
            elif side == "sell" and current_price >= target_price:
                # Credit USDT to wallet minus fee
                gross_usdt = order["amount"] * target_price
                fee_usdt = gross_usdt * self.paper_fee_rate
                self.paper_balance_usdt += (gross_usdt - fee_usdt)
                self._save_paper_state()
                return True
            return False

        # Live mode fill check
        order_status = await self.client.fetch_order(order["order_id"], sym)
        return order_status["status"] == "closed"

    async def cancel_order(self, order: Dict[str, Any]) -> bool:
        """Cancels an open order and unlocks allocated assets."""
        order_id = order.get("order_id") or order.get("id")
        sym = order.get("symbol") or self.symbol
        side = order.get("side", "buy")
        cost = float(order.get("cost_usd") or (float(order.get("price", 0)) * float(order.get("amount", 0))))
        amount = float(order.get("amount", 0))
        base = sym.split("/")[0]

        if self.mode == "paper":
            if side == "buy":
                self.paper_balance_usdt += cost
            elif side == "sell":
                self.paper_balance_crypto[base] = self.paper_balance_crypto.get(base, 0.0) + amount
            self._save_paper_state()
            return True

        if self.client:
            await self.client.cancel_order(order_id, sym)
            return True
        return False

        if self.client:
            await self.client.cancel_order(order_id, sym)
            return True
        return False

    async def close(self) -> None:
        if self.client:
            await self.client.close()
