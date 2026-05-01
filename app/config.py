from __future__ import annotations

from dataclasses import dataclass
import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    alpaca_api_key: str | None = os.getenv("ALPACA_API_KEY")
    alpaca_secret_key: str | None = os.getenv("ALPACA_SECRET_KEY")
    alpaca_paper: bool = _bool_env("ALPACA_PAPER", True)
    alpaca_enable_trading: bool = _bool_env("ALPACA_ENABLE_TRADING", False)
    require_manual_approval: bool = _bool_env("REQUIRE_MANUAL_APPROVAL", True)

    newsapi_key: str | None = os.getenv("NEWSAPI_KEY")
    finnhub_api_key: str | None = os.getenv("FINNHUB_API_KEY")

    database_url: str = os.getenv("DATABASE_URL", "sqlite:///data/trading_bot.sqlite3")
    max_trade_dollars: float = float(os.getenv("MAX_TRADE_DOLLARS", "25"))
    max_daily_loss_dollars: float = float(os.getenv("MAX_DAILY_LOSS_DOLLARS", "20"))
    max_open_positions: int = int(os.getenv("MAX_OPEN_POSITIONS", "3"))
    max_daily_losses: int = int(os.getenv("MAX_DAILY_LOSSES", "2"))


settings = Settings()
