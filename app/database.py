from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    insert,
)
from sqlalchemy.engine import Engine

from app.models import NewsItem, RiskDecision, Signal


metadata = MetaData()

news_items = Table(
    "news_items",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", Text, nullable=False),
    Column("url", Text, nullable=False),
    Column("source", String(100), nullable=False),
    Column("published_at", DateTime(timezone=True), nullable=False),
    Column("summary", Text, nullable=False, default=""),
    Column("collected_at", DateTime(timezone=True), nullable=False),
)

signals = Table(
    "signals",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("news_item_id", Integer, ForeignKey("news_items.id"), nullable=False),
    Column("action", String(20), nullable=False),
    Column("ticker", String(20), nullable=False),
    Column("sector", String(80), nullable=False),
    Column("confidence", Float, nullable=False),
    Column("reason", Text, nullable=False),
    Column("source_url", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

risk_decisions = Table(
    "risk_decisions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("signal_id", Integer, ForeignKey("signals.id"), nullable=False),
    Column("approved", Boolean, nullable=False),
    Column("trade_dollars", Float, nullable=False),
    Column("reasons_json", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

executions = Table(
    "executions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("signal_id", Integer, ForeignKey("signals.id"), nullable=False),
    Column("status", String(40), nullable=False),
    Column("message", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)


class AnalysisStore:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        _ensure_sqlite_parent(database_url)
        self.engine = create_engine(database_url, future=True)

    def initialize(self) -> None:
        metadata.create_all(self.engine)

    def log_analysis(
        self,
        item: NewsItem,
        signal: Signal,
        risk: RiskDecision,
        execution_message: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        execution_status = _execution_status(execution_message)

        with self.engine.begin() as connection:
            news_id = connection.execute(
                insert(news_items).values(
                    title=item.title,
                    url=item.url,
                    source=item.source,
                    published_at=item.published_at,
                    summary=item.summary,
                    collected_at=now,
                )
            ).inserted_primary_key[0]

            signal_id = connection.execute(
                insert(signals).values(
                    news_item_id=news_id,
                    action=signal.action.value,
                    ticker=signal.ticker,
                    sector=signal.sector,
                    confidence=signal.confidence,
                    reason=signal.reason,
                    source_url=signal.source_url,
                    created_at=signal.created_at,
                )
            ).inserted_primary_key[0]

            connection.execute(
                insert(risk_decisions).values(
                    signal_id=signal_id,
                    approved=risk.approved,
                    trade_dollars=risk.trade_dollars,
                    reasons_json=json.dumps(list(risk.reasons)),
                    created_at=now,
                )
            )

            connection.execute(
                insert(executions).values(
                    signal_id=signal_id,
                    status=execution_status,
                    message=execution_message,
                    created_at=now,
                )
            )


def initialize_database(database_url: str) -> Engine:
    store = AnalysisStore(database_url)
    store.initialize()
    return store.engine


def _ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    raw_path = database_url.removeprefix("sqlite:///")
    if raw_path in {":memory:", ""}:
        return
    Path(raw_path).expanduser().parent.mkdir(parents=True, exist_ok=True)


def _execution_status(message: str) -> str:
    if message.startswith("paper order submitted"):
        return "submitted"
    if message.startswith("blocked"):
        return "blocked"
    if message.startswith("dry-run") or message == "not requested":
        return "dry_run"
    return "unknown"
