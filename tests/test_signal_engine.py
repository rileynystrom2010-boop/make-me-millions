from __future__ import annotations

from datetime import datetime, timezone

from app.models import NewsItem, SignalAction
from app.signal_engine import SignalEngine


def test_tariff_news_maps_to_industrials_and_sell_recommendation() -> None:
    item = NewsItem(
        title="New tariff on imported steel announced",
        summary="The announcement includes duties on aluminum and manufacturing imports.",
        url="https://example.com/tariff",
        source="test",
        published_at=datetime.now(timezone.utc),
    )

    signal = SignalEngine().generate_signal(item)

    assert signal.action == SignalAction.SELL
    assert signal.ticker == "XLI"
    assert signal.sector == "industrials_materials"


def test_oil_permit_news_maps_to_energy_buy_recommendation() -> None:
    item = NewsItem(
        title="Administration approves new oil drilling permit",
        summary="Energy regulators grant permit approval.",
        url="https://example.com/oil",
        source="test",
        published_at=datetime.now(timezone.utc),
    )

    signal = SignalEngine().generate_signal(item)

    assert signal.action == SignalAction.BUY
    assert signal.ticker == "XLE"
    assert signal.sector == "energy"


def test_unrelated_news_holds_cash() -> None:
    item = NewsItem(
        title="Ceremonial proclamation released",
        summary="No obvious market-sensitive content.",
        url="https://example.com/hold",
        source="test",
        published_at=datetime.now(timezone.utc),
    )

    signal = SignalEngine().generate_signal(item)

    assert signal.action == SignalAction.HOLD
    assert signal.ticker == "CASH"

