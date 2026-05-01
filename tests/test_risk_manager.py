from __future__ import annotations

from datetime import datetime, timezone

from app.config import Settings
from app.models import PortfolioState, Signal, SignalAction
from app.risk_manager import RiskManager


def _settings(require_manual_approval: bool = False) -> Settings:
    return Settings(
        alpaca_api_key=None,
        alpaca_secret_key=None,
        alpaca_paper=True,
        alpaca_enable_trading=False,
        require_manual_approval=require_manual_approval,
        newsapi_key=None,
        finnhub_api_key=None,
        database_url="sqlite:///data/test.sqlite3",
        max_trade_dollars=25,
        max_daily_loss_dollars=20,
        max_open_positions=3,
        max_daily_losses=2,
    )


def test_buy_signal_can_pass_when_manual_approval_disabled() -> None:
    signal = Signal(
        action=SignalAction.BUY,
        ticker="XLE",
        sector="energy",
        confidence=0.7,
        reason="test",
        source_url="https://example.com",
        created_at=datetime.now(timezone.utc),
    )

    decision = RiskManager(_settings()).evaluate(signal, PortfolioState())

    assert decision.approved is True
    assert decision.trade_dollars == 25


def test_manual_approval_blocks_trade_by_default() -> None:
    signal = Signal(
        action=SignalAction.BUY,
        ticker="XLE",
        sector="energy",
        confidence=0.7,
        reason="test",
        source_url="https://example.com",
        created_at=datetime.now(timezone.utc),
    )

    decision = RiskManager(_settings(require_manual_approval=True)).evaluate(signal, PortfolioState())

    assert decision.approved is False
    assert "manual approval required before any order" in decision.reasons


def test_daily_loss_limit_blocks_trade() -> None:
    signal = Signal(
        action=SignalAction.BUY,
        ticker="XLE",
        sector="energy",
        confidence=0.7,
        reason="test",
        source_url="https://example.com",
        created_at=datetime.now(timezone.utc),
    )

    decision = RiskManager(_settings()).evaluate(signal, PortfolioState(daily_realized_loss=20))

    assert decision.approved is False
    assert "max daily loss reached" in decision.reasons

