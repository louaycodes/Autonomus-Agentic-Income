"""Trading Agent Configuration Module."""
import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class TradingConfig(BaseModel):
    # Trading Mode: 'paper' (real live prices, zero capital risk) or 'live' (exchange API keys)
    trading_mode: str = Field(default_factory=lambda: os.getenv("TRADING_MODE", "paper").lower())
    
    # Target Asset & Capital
    exchange_name: str = Field(default_factory=lambda: os.getenv("EXCHANGE_NAME", "binance").lower())
    symbol: str = Field(default_factory=lambda: os.getenv("SYMBOL", "SOL/USDT"))
    total_capital_usd: float = Field(default_factory=lambda: float(os.getenv("TOTAL_CAPITAL_USD", "100.0")))
    
    # Grid Parameters
    grid_levels: int = Field(default_factory=lambda: int(os.getenv("GRID_LEVELS", "10")))
    grid_step_percent: float = Field(default_factory=lambda: float(os.getenv("GRID_STEP_PERCENT", "1.2"))) # 1.2% profit per grid
    range_half_span_percent: float = Field(default_factory=lambda: float(os.getenv("RANGE_HALF_SPAN_PERCENT", "8.0"))) # +/- 8% price envelope
    
    # Strategy Safeguards
    enable_trend_guard: bool = Field(default_factory=lambda: os.getenv("ENABLE_TREND_GUARD", "true").lower() == "true")
    rsi_oversold_threshold: float = Field(default_factory=lambda: float(os.getenv("RSI_OVERSOLD_THRESHOLD", "28.0")))
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
