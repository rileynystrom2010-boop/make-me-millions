from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean
import socket

import requests
from sqlalchemy import select

from app.config import settings
from app.database import AnalysisStore, news_items, risk_decisions, signals


@dataclass(frozen=True)
class LoggedSignal:
    signal_id: int
    source: str
    title: str
    ticker: str
    sector: str
    trade_dollars: float
    created_at: datetime


@dataclass(frozen=True)
class SignalOutcome:
    signal: LoggedSignal
    entry_price: float | None
    exit_price: float | None
    return_pct: float | None
    profit_dollars: float | None
    status: str


class AlpacaPriceProvider:
    def __init__(self) -> None:
        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            raise ValueError("Alpaca keys are missing. Add ALPACA_API_KEY and ALPACA_SECRET_KEY to .env.")

        from alpaca.data.historical import StockHistoricalDataClient

        self.client = StockHistoricalDataClient(settings.alpaca_api_key, settings.alpaca_secret_key)

    def daily_closes(self, ticker: str, start: datetime, end: datetime) -> list[tuple[datetime, float]]:
        from alpaca.data.enums import DataFeed
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        request = StockBarsRequest(
            symbol_or_symbols=ticker,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            feed=DataFeed.IEX,
        )
        bars = self.client.get_stock_bars(request)
        frame = bars.df
        if frame.empty:
            return []

        rows: list[tuple[datetime, float]] = []
        ticker_frame = frame.xs(ticker) if "symbol" in frame.index.names else frame
        for timestamp, row in ticker_frame.iterrows():
            rows.append((_as_utc(timestamp.to_pydatetime()), float(row["close"])))
        return rows


def load_approved_buy_signals(limit: int) -> list[LoggedSignal]:
    store = AnalysisStore(settings.database_url)
    store.initialize()

    query = (
        select(
            signals.c.id,
            news_items.c.source,
            news_items.c.title,
            signals.c.ticker,
            signals.c.sector,
            risk_decisions.c.trade_dollars,
            signals.c.created_at,
        )
        .join(news_items, news_items.c.id == signals.c.news_item_id)
        .join(risk_decisions, risk_decisions.c.signal_id == signals.c.id)
        .where(signals.c.action == "buy")
        .where(risk_decisions.c.approved.is_(True))
        .order_by(signals.c.created_at.desc())
        .limit(limit)
    )

    with store.engine.connect() as connection:
        return [
            LoggedSignal(
                signal_id=row.id,
                source=row.source,
                title=row.title,
                ticker=row.ticker,
                sector=row.sector,
                trade_dollars=row.trade_dollars,
                created_at=_as_utc(row.created_at),
            )
            for row in connection.execute(query)
        ]


def evaluate_signal(
    signal: LoggedSignal,
    price_provider: AlpacaPriceProvider,
    hold_days: int,
) -> SignalOutcome:
    start = signal.created_at - timedelta(days=1)
    end = signal.created_at + timedelta(days=hold_days + 10)
    closes = price_provider.daily_closes(signal.ticker, start, end)
    closes_after_signal = [(date, close) for date, close in closes if date >= signal.created_at]

    if len(closes_after_signal) <= hold_days:
        return SignalOutcome(signal, None, None, None, None, "pending")

    entry_price = closes_after_signal[0][1]
    exit_price = closes_after_signal[hold_days][1]
    return_pct = (exit_price - entry_price) / entry_price
    profit_dollars = signal.trade_dollars * return_pct
    return SignalOutcome(signal, entry_price, exit_price, return_pct, profit_dollars, "complete")


def print_report(outcomes: list[SignalOutcome], hold_days: int) -> None:
    complete = [outcome for outcome in outcomes if outcome.status == "complete"]
    pending = [outcome for outcome in outcomes if outcome.status == "pending"]
    errors = [outcome for outcome in outcomes if outcome.status.startswith("price_error")]

    print(f"Performance report: {hold_days}-trading-day hold")
    print(f"complete={len(complete)} pending={len(pending)} price_errors={len(errors)}")

    if complete:
        wins = [outcome for outcome in complete if (outcome.profit_dollars or 0) > 0]
        total_profit = sum(outcome.profit_dollars or 0 for outcome in complete)
        avg_return = mean(outcome.return_pct or 0 for outcome in complete)
        print(f"win_rate={len(wins) / len(complete):.1%}")
        print(f"avg_return={avg_return:.2%}")
        print(f"estimated_profit=${total_profit:.2f}")

    print()
    for outcome in outcomes:
        signal = outcome.signal
        if outcome.status == "pending":
            print(f"PENDING {signal.ticker} {signal.source}: {signal.title[:90]}")
            continue
        if outcome.status.startswith("price_error"):
            print(f"PRICE ERROR {signal.ticker} {signal.source}: {outcome.status[:140]}")
            continue

        print(
            f"{signal.ticker} {outcome.return_pct:.2%} "
            f"${outcome.profit_dollars:.2f} "
            f"{signal.source}: {signal.title[:90]}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate logged buy signals against Alpaca historical prices")
    parser.add_argument("--hold-days", type=int, default=3, help="Trading days to hold each signal")
    parser.add_argument("--limit", type=int, default=50, help="Maximum approved buy signals to evaluate")
    args = parser.parse_args()

    logged_signals = load_approved_buy_signals(limit=args.limit)
    if not logged_signals:
        print("No approved buy signals found in the database yet.")
        return 0

    provider = AlpacaPriceProvider()
    outcomes: list[SignalOutcome] = []
    for signal in logged_signals:
        try:
            outcomes.append(evaluate_signal(signal, provider, args.hold_days))
        except Exception as exc:
            outcomes.append(SignalOutcome(signal, None, None, None, None, f"price_error: {_friendly_error(exc)}"))
    print_report(outcomes, hold_days=args.hold_days)
    return 0


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _friendly_error(exc: Exception) -> str:
    message = str(exc)
    if isinstance(exc, requests.ConnectionError) and "NameResolutionError" in message:
        return "DNS failed for Alpaca market data. Check internet, DNS, VPN, firewall, or try again later."
    if isinstance(exc, requests.Timeout):
        return "Alpaca market data request timed out. Try again or increase network reliability."
    if isinstance(exc, socket.gaierror):
        return "DNS failed. Your computer could not resolve the market data host."
    return message


if __name__ == "__main__":
    raise SystemExit(main())
