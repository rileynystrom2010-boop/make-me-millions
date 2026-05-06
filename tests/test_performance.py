from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.performance import LoggedSignal, evaluate_signal


class FakePriceProvider:
    def __init__(self, closes: list[float]) -> None:
        self.closes = closes

    def daily_closes(self, ticker: str, start: datetime, end: datetime) -> list[tuple[datetime, float]]:
        return [
            (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index), close)
            for index, close in enumerate(self.closes)
        ]


def test_evaluate_signal_calculates_profit() -> None:
    signal = LoggedSignal(
        signal_id=1,
        source="EIA",
        title="Energy signal",
        ticker="XLE",
        sector="energy",
        trade_dollars=10,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    outcome = evaluate_signal(signal, FakePriceProvider([100, 105, 110]), hold_days=2)

    assert outcome.status == "complete"
    assert outcome.return_pct == 0.10
    assert outcome.profit_dollars == 1.0


def test_evaluate_signal_marks_recent_signal_pending() -> None:
    signal = LoggedSignal(
        signal_id=1,
        source="EIA",
        title="Energy signal",
        ticker="XLE",
        sector="energy",
        trade_dollars=10,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    outcome = evaluate_signal(signal, FakePriceProvider([100]), hold_days=2)

    assert outcome.status == "pending"
