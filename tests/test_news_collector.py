from __future__ import annotations

from datetime import datetime, timezone

from app.models import NewsItem
from app.news_collector import NewsCollector


def test_collect_all_can_skip_federal_register(monkeypatch) -> None:
    collector = NewsCollector(timeout_seconds=1)
    called = {"federal_register": False}

    def fake_white_house(limit: int) -> list[NewsItem]:
        return [
            NewsItem(
                title="White House item",
                url="https://example.com/white-house",
                source="White House",
                published_at=datetime.now(timezone.utc),
            )
        ]

    def fake_federal_register(limit: int) -> list[NewsItem]:
        called["federal_register"] = True
        return []

    monkeypatch.setattr(collector, "fetch_white_house", fake_white_house)
    monkeypatch.setattr(collector, "fetch_federal_register", fake_federal_register)

    items = collector.collect_all(
        limit=10,
        include_federal_register=False,
        include_newsapi=False,
        include_treasury=False,
        include_sec=False,
        include_eia=False,
    )

    assert called["federal_register"] is False
    assert [item.source for item in items] == ["White House"]


def test_collect_all_can_skip_all_sources() -> None:
    collector = NewsCollector(timeout_seconds=1)

    items = collector.collect_all(
        include_white_house=False,
        include_federal_register=False,
        include_newsapi=False,
        include_treasury=False,
        include_sec=False,
        include_eia=False,
    )

    assert items == []
