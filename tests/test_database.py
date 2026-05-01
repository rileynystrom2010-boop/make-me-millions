from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select

from app.database import AnalysisStore, executions, news_items, risk_decisions, signals
from app.models import NewsItem, RiskDecision, Signal, SignalAction


def test_log_analysis_writes_audit_rows(tmp_path) -> None:
    store = AnalysisStore(f"sqlite:///{tmp_path / 'audit.sqlite3'}")
    store.initialize()

    item = NewsItem(
        title="Administration approves new oil drilling permit",
        url="https://example.com/oil",
        source="test",
        published_at=datetime.now(timezone.utc),
        summary="Energy regulators grant permit approval.",
    )
    signal = Signal(
        action=SignalAction.BUY,
        ticker="XLE",
        sector="energy",
        confidence=0.7,
        reason="matched keywords: oil",
        source_url=item.url,
    )
    risk = RiskDecision(
        approved=False,
        trade_dollars=0,
        reasons=("manual approval required before any order",),
    )

    store.log_analysis(item, signal, risk, "not requested")

    with store.engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(news_items)) == 1
        assert connection.scalar(select(func.count()).select_from(signals)) == 1
        assert connection.scalar(select(func.count()).select_from(risk_decisions)) == 1
        assert connection.scalar(select(func.count()).select_from(executions)) == 1
