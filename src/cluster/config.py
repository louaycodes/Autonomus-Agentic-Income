"""Cluster Configuration Module."""
import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment from project root .env if present
load_dotenv()

class ClusterConfig(BaseModel):
    # Operating Mode
    simulation_mode: bool = Field(default_factory=lambda: os.getenv("SIMULATION_MODE", "true").lower() == "true")
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "production"))
    
    # Storage
    data_dir: Path = Field(default_factory=lambda: Path(os.getenv("DATA_DIR", "./data")))
    db_name: str = Field(default_factory=lambda: os.getenv("DB_NAME", "cluster.db"))
    
    # Engine A (Gateway & Ingestion)
    api_host: str = Field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    api_port: int = Field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    rapidapi_proxy_secret: str = Field(default_factory=lambda: os.getenv("RAPIDAPI_PROXY_SECRET", ""))
    master_api_key: str = Field(default_factory=lambda: os.getenv("MASTER_API_KEY", "cluster_secret_master_key_2026"))
    scout_interval_seconds: int = Field(default_factory=lambda: int(os.getenv("SCOUT_INTERVAL_SECONDS", "3600")))
    
    # Engine B (Arbitrage)
    polymarket_clob_api: str = Field(default_factory=lambda: os.getenv("POLYMARKET_CLOB_API", "https://clob.polymarket.com"))
    polygon_rpc_url: str = Field(default_factory=lambda: os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com"))
    arbitrage_poll_interval: int = Field(default_factory=lambda: int(os.getenv("ARBITRAGE_POLL_INTERVAL", "30")))
    min_spread_threshold: float = Field(default_factory=lambda: float(os.getenv("MIN_SPREAD_THRESHOLD", "0.08"))) # 8% min spread
    max_trade_allocation_usd: float = Field(default_factory=lambda: float(os.getenv("MAX_TRADE_ALLOCATION_USD", "20.0"))) # Max 20$ per trade
    
    # Sentinel & Notifications
    telegram_bot_token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = Field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))
    sentinel_check_interval: int = Field(default_factory=lambda: int(os.getenv("SENTINEL_CHECK_INTERVAL", "60")))
    daily_report_hour_utc: int = Field(default_factory=lambda: int(os.getenv("DAILY_REPORT_HOUR_UTC", "23")))

    @property
    def db_path(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / self.db_name

config = ClusterConfig()
