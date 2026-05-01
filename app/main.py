from __future__ import annotations

import argparse

from app.alpaca_client import AlpacaPaperClient
from app.models import PortfolioState
from app.news_collector import NewsCollector
from app.risk_manager import RiskManager
from app.signal_engine import SignalEngine


def run(limit: int, execute: bool) -> int:
    collector = NewsCollector()
    engine = SignalEngine()
    risk_manager = RiskManager()
    broker = AlpacaPaperClient()
    portfolio = PortfolioState()

    items = collector.collect_all(limit=limit)
    if not items:
        print("No announcements/news collected.")
        return 0

    for item in items:
        signal = engine.generate_signal(item)
        risk = risk_manager.evaluate(signal, portfolio)
        print(f"{item.source}: {item.title}")
        print(f"  signal={signal.action.value} ticker={signal.ticker} sector={signal.sector} confidence={signal.confidence:.2f}")
        print(f"  reason={signal.reason}")
        print(f"  risk={'approved' if risk.approved else 'blocked'} trade_dollars={risk.trade_dollars:.2f}")
        if risk.reasons:
            print(f"  risk_reasons={'; '.join(risk.reasons)}")
        if execute:
            print(f"  execution={broker.submit_fractional_order(signal, risk)}")
        print(f"  url={item.url}")
        print()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="News-driven paper trading signal bot")
    parser.add_argument("--limit", type=int, default=10, help="Maximum items to analyze")
    parser.add_argument("--execute", action="store_true", help="Attempt paper orders if enabled and approved")
    args = parser.parse_args()
    return run(limit=args.limit, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())

