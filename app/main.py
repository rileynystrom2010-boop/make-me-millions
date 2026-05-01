from __future__ import annotations

import argparse

from app.alpaca_client import AlpacaPaperClient
from app.config import settings
from app.database import AnalysisStore
from app.models import PortfolioState
from app.news_collector import NewsCollector
from app.risk_manager import RiskManager
from app.signal_engine import SignalEngine


def run(
    limit: int,
    execute: bool,
    log: bool,
    timeout_seconds: float,
    include_white_house: bool,
    include_federal_register: bool,
    include_newsapi: bool,
) -> int:
    collector = NewsCollector(timeout_seconds=timeout_seconds)
    engine = SignalEngine()
    risk_manager = RiskManager()
    broker = AlpacaPaperClient()
    portfolio = PortfolioState()
    store = AnalysisStore(settings.database_url) if log else None
    if store is not None:
        store.initialize()

    items = collector.collect_all(
        limit=limit,
        include_white_house=include_white_house,
        include_federal_register=include_federal_register,
        include_newsapi=include_newsapi,
    )
    if not items:
        print("No announcements/news collected.")
        return 0

    for item in items:
        signal = engine.generate_signal(item)
        risk = risk_manager.evaluate(signal, portfolio)
        execution_message = "not requested"
        print(f"{item.source}: {item.title}")
        print(f"  signal={signal.action.value} ticker={signal.ticker} sector={signal.sector} confidence={signal.confidence:.2f}")
        print(f"  reason={signal.reason}")
        print(f"  risk={'approved' if risk.approved else 'blocked'} trade_dollars={risk.trade_dollars:.2f}")
        if risk.reasons:
            print(f"  risk_reasons={'; '.join(risk.reasons)}")
        if execute:
            execution_message = broker.submit_fractional_order(signal, risk)
            print(f"  execution={execution_message}")
        if store is not None:
            store.log_analysis(item, signal, risk, execution_message)
            print(f"  logged={settings.database_url}")
        print(f"  url={item.url}")
        print()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="News-driven paper trading signal bot")
    parser.add_argument("--limit", type=int, default=10, help="Maximum items to analyze")
    parser.add_argument("--execute", action="store_true", help="Attempt paper orders if enabled and approved")
    parser.add_argument("--no-log", action="store_true", help="Do not write analysis results to the database")
    parser.add_argument("--check-alpaca", action="store_true", help="Validate Alpaca paper account credentials")
    parser.add_argument("--timeout", type=float, default=5, help="Seconds to wait for each news source request")
    parser.add_argument("--skip-white-house", action="store_true", help="Skip White House source")
    parser.add_argument("--skip-federal-register", action="store_true", help="Skip Federal Register source")
    parser.add_argument("--skip-newsapi", action="store_true", help="Skip NewsAPI source")
    args = parser.parse_args()
    if args.check_alpaca:
        print(AlpacaPaperClient().check_connection())
        return 0
    return run(
        limit=args.limit,
        execute=args.execute,
        log=not args.no_log,
        timeout_seconds=args.timeout,
        include_white_house=not args.skip_white_house,
        include_federal_register=not args.skip_federal_register,
        include_newsapi=not args.skip_newsapi,
    )


if __name__ == "__main__":
    raise SystemExit(main())
