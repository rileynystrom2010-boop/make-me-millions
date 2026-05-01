from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class SignalAction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass(frozen=True)
class NewsItem:
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str = ""

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.summary}".strip()


@dataclass(frozen=True)
class Classification:
    sector: str
    keywords: tuple[str, ...]
    tickers: tuple[str, ...]
    confidence: float
    rationale: str


@dataclass(frozen=True)
class Signal:
    action: SignalAction
    ticker: str
    sector: str
    confidence: float
    reason: str
    source_url: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    trade_dollars: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PortfolioState:
    open_positions: int = 0
    daily_realized_loss: float = 0.0
    daily_loss_count: int = 0

