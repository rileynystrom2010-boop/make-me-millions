from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from app.config import settings
from app.models import NewsItem


DEFAULT_TIMEOUT_SECONDS = 5


class NewsCollector:
    """Collects government announcements and optional market news."""

    white_house_url = "https://www.whitehouse.gov/presidential-actions/"
    federal_register_url = "https://www.federalregister.gov/api/v1/articles.json"
    newsapi_url = "https://newsapi.org/v2/everything"
    treasury_url = "https://home.treasury.gov/news/press-releases"
    sec_press_url = "https://www.sec.gov/newsroom/press-releases"
    eia_press_url = "https://www.eia.gov/pressroom/releases.php"

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds

    def collect_all(
        self,
        limit: int = 20,
        include_white_house: bool = True,
        include_federal_register: bool = True,
        include_newsapi: bool = True,
        include_treasury: bool = True,
        include_sec: bool = True,
        include_eia: bool = True,
    ) -> list[NewsItem]:
        items: list[NewsItem] = []
        collectors = []
        if include_white_house:
            collectors.append(self.fetch_white_house)
        if include_federal_register:
            collectors.append(self.fetch_federal_register)
        if include_treasury:
            collectors.append(self.fetch_treasury)
        if include_sec:
            collectors.append(self.fetch_sec_press_releases)
        if include_eia:
            collectors.append(self.fetch_eia_press_releases)
        if include_newsapi:
            collectors.append(self.fetch_newsapi)

        for collector in collectors:
            try:
                items.extend(collector(limit=limit))
            except requests.Timeout as exc:
                print(f"collector warning: {collector.__name__} timed out after {self.timeout_seconds:g}s: {exc}")
            except requests.RequestException as exc:
                print(f"collector warning: {collector.__name__} failed: {exc}")
        return _dedupe(items)[:limit]

    def fetch_white_house(self, limit: int = 20) -> list[NewsItem]:
        response = self.session.get(self.white_house_url, timeout=self.timeout_seconds)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        items: list[NewsItem] = []
        for link in soup.select("h2 a[href*='/presidential-actions/']"):
            title = " ".join(link.get_text(" ", strip=True).split())
            url = link.get("href", "")
            if not title or not url or url.rstrip("/") == self.white_house_url.rstrip("/"):
                continue
            items.append(
                NewsItem(
                    title=title,
                    url=url,
                    source="White House",
                    published_at=datetime.now(timezone.utc),
                )
            )
            if len(items) >= limit:
                break
        return items

    def fetch_federal_register(self, limit: int = 20) -> list[NewsItem]:
        params = {
            "per_page": limit,
            "order": "newest",
            "conditions[type][]": ["RULE", "PRORULE", "NOTICE", "PRESDOCU"],
        }
        response = self.session.get(self.federal_register_url, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()

        items: list[NewsItem] = []
        for article in payload.get("results", []):
            published = _parse_datetime(article.get("publication_date"))
            items.append(
                NewsItem(
                    title=article.get("title", "Untitled Federal Register article"),
                    summary=article.get("abstract") or "",
                    url=article.get("html_url") or article.get("document_url") or "",
                    source="Federal Register",
                    published_at=published,
                )
            )
        return items

    def fetch_newsapi(self, limit: int = 20) -> list[NewsItem]:
        if not settings.newsapi_key:
            return []

        params = {
            "q": "(tariff OR oil OR semiconductor OR pharma OR banking OR sanctions) AND (White House OR Trump OR federal)",
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": limit,
            "apiKey": settings.newsapi_key,
        }
        response = self.session.get(self.newsapi_url, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()

        items: list[NewsItem] = []
        for article in payload.get("articles", []):
            items.append(
                NewsItem(
                    title=article.get("title") or "Untitled news article",
                    summary=article.get("description") or "",
                    url=article.get("url") or "",
                    source=(article.get("source") or {}).get("name", "NewsAPI"),
                    published_at=_parse_datetime(article.get("publishedAt")),
                )
            )
        return items

    def fetch_treasury(self, limit: int = 20) -> list[NewsItem]:
        response = self.session.get(self.treasury_url, timeout=self.timeout_seconds)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        items: list[NewsItem] = []
        for link in soup.select("a[href*='/news/press-releases/']"):
            title = " ".join(link.get_text(" ", strip=True).split())
            url = _absolute_url(link.get("href", ""), "https://home.treasury.gov")
            if not title or url.rstrip("/") == self.treasury_url.rstrip("/"):
                continue
            items.append(
                NewsItem(
                    title=title,
                    url=url,
                    source="Treasury",
                    published_at=datetime.now(timezone.utc),
                )
            )
            if len(items) >= limit:
                break
        return items

    def fetch_sec_press_releases(self, limit: int = 20) -> list[NewsItem]:
        response = self.session.get(
            self.sec_press_url,
            timeout=self.timeout_seconds,
            headers={"User-Agent": "make-millions trading bot contact@example.com"},
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        items: list[NewsItem] = []
        for link in soup.select("a[href*='/newsroom/press-releases/'], a[href*='/news/press-release/']"):
            title = " ".join(link.get_text(" ", strip=True).split())
            url = _absolute_url(link.get("href", ""), "https://www.sec.gov")
            if not title or url.rstrip("/") == self.sec_press_url.rstrip("/"):
                continue
            items.append(
                NewsItem(
                    title=title,
                    url=url,
                    source="SEC",
                    published_at=datetime.now(timezone.utc),
                )
            )
            if len(items) >= limit:
                break
        return items

    def fetch_eia_press_releases(self, limit: int = 20) -> list[NewsItem]:
        response = self.session.get(self.eia_press_url, timeout=self.timeout_seconds)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        items: list[NewsItem] = []
        for link in soup.select("a[href*='/pressroom/releases/'], a[href*='releases.php']"):
            title = " ".join(link.get_text(" ", strip=True).split())
            url = _absolute_url(link.get("href", ""), "https://www.eia.gov")
            if not title or url.rstrip("/") == self.eia_press_url.rstrip("/"):
                continue
            items.append(
                NewsItem(
                    title=title,
                    url=url,
                    source="EIA",
                    published_at=datetime.now(timezone.utc),
                )
            )
            if len(items) >= limit:
                break
        return items


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _dedupe(items: Iterable[NewsItem]) -> list[NewsItem]:
    seen: set[str] = set()
    unique: list[NewsItem] = []
    for item in sorted(items, key=lambda news: news.published_at, reverse=True):
        key = item.url or item.title.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _absolute_url(url: str, base_url: str) -> str:
    if url.startswith("http"):
        return url
    if url.startswith("/"):
        return f"{base_url}{url}"
    return url
