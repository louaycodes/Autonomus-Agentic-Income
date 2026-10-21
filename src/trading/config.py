"""Trading Agent Configuration Module."""
import os
from typing import List
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class TradingConfig(BaseModel):
    # Trading Mode: 'paper' (real live prices, zero capital risk) or 'live' (exchange API keys)
    trading_mode: str = Field(default_factory=lambda: os.getenv("TRADING_MODE", "paper").lower())
    
    # Target Asset Portfolio & Capital (High Volatility Scalping Basket)
    exchange_name: str = Field(default_factory=lambda: os.getenv("EXCHANGE_NAME", "binance").lower())
    symbols: List[str] = Field(default_factory=lambda: [s.strip() for s in os.getenv("SYMBOLS", "BTC/USDT,SOL/USDT,ETH/USDT").split(",") if s.strip()])
    total_capital_usd: float = Field(default_factory=lambda: float(os.getenv("TOTAL_CAPITAL_USD", "1000.0")))
    compound_profits: bool = Field(default_factory=lambda: os.getenv("COMPOUND_PROFITS", "true").lower() == "true")
    leverage: int = Field(default_factory=lambda: int(os.getenv("LEVERAGE", "1"))) # Default spot 1x
    
    # Backward compatibility helper for single symbol
    @property
    def symbol(self) -> str:
        return self.symbols[0] if self.symbols else "SOL/USDT"
    
    # Grid Parameters (High-Frequency Micro-Oscillations)
    grid_levels: int = Field(default_factory=lambda: int(os.getenv("GRID_LEVELS", "8")))
    grid_step_percent: float = Field(default_factory=lambda: float(os.getenv("GRID_STEP_PERCENT", "0.8"))) # 0.8% high-frequency scalping spread
    range_half_span_percent: float = Field(default_factory=lambda: float(os.getenv("RANGE_HALF_SPAN_PERCENT", "6.0")))
    stale_order_max_drop_percent: float = Field(default_factory=lambda: float(os.getenv("STALE_ORDER_MAX_DROP_PERCENT", "2.5")))
    
    # Dual-Engine Strategy Safeguards
    enable_trend_guard: bool = Field(default_factory=lambda: os.getenv("ENABLE_TREND_GUARD", "true").lower() == "true")
    enable_momentum_breakout: bool = Field(default_factory=lambda: os.getenv("ENABLE_MOMENTUM_BREAKOUT", "true").lower() == "true")
    risk_per_trade_percent: float = Field(default_factory=lambda: float(os.getenv("RISK_PER_TRADE_PERCENT", "2.0")))
    min_confluence_score: float = Field(default_factory=lambda: float(os.getenv("MIN_CONFLUENCE_SCORE", "45.0")))
    rsi_oversold_threshold: float = Field(default_factory=lambda: float(os.getenv("RSI_OVERSOLD_THRESHOLD", "25.0")))
    stop_loss_percent: float = Field(default_factory=lambda: float(os.getenv("STOP_LOSS_PERCENT", "15.0")))
    
    # Exchange API Credentials (for live mode)
    exchange_api_key: str = Field(default_factory=lambda: os.getenv("EXCHANGE_API_KEY", ""))
    exchange_api_secret: str = Field(default_factory=lambda: os.getenv("EXCHANGE_API_SECRET", ""))
    exchange_password: str = Field(default_factory=lambda: os.getenv("EXCHANGE_PASSWORD", ""))
    
    # Storage & VPS Paths
    data_dir: Path = Field(default_factory=lambda: Path(os.getenv("DATA_DIR", "./data")))
    db_name: str = Field(default_factory=lambda: os.getenv("DB_NAME", "trading.db"))
    
    # Telegram Bot Controls
    telegram_bot_token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = Field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))
    poll_interval_seconds: int = Field(default_factory=lambda: int(os.getenv("POLL_INTERVAL_SECONDS", "3")))
    daily_report_hour_utc: int = Field(default_factory=lambda: int(os.getenv("DAILY_REPORT_HOUR_UTC", "23")))

    @property
    def db_path(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / self.db_name

config = TradingConfig()
