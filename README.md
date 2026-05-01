# make-me-millions

A conservative, paper-first Python trading bot that watches government announcements and market news, classifies likely affected sectors, and generates ETF-focused trading signals.

This project is research software, not financial advice. The default configuration does not place trades.

## What It Does

- Collects announcements from White House Presidential Actions and the Federal Register.
- Optionally reads NewsAPI results when `NEWSAPI_KEY` is configured.
- Maps keywords like `tariff`, `oil`, `semiconductor`, and `pharma` to sectors and ETFs.
- Generates simple `buy`, `sell`, or `hold` signals.
- Applies strict risk rules before any paper order.
- Keeps Alpaca execution disabled unless explicitly turned on.

## Project Layout

```text
app/
  main.py
  news_collector.py
  signal_engine.py
  risk_manager.py
  alpaca_client.py
  config.py
  models.py
data/
tests/
.env.example
requirements.txt
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run Signal Research

```bash
python -m app.main --limit 10
```

This collects recent announcements/news and prints recommendations. It does not trade.

## Paper Trading Gate

Paper execution requires all of these:

```env
ALPACA_API_KEY=...
ALPACA_SECRET_KEY=...
ALPACA_PAPER=true
ALPACA_ENABLE_TRADING=true
REQUIRE_MANUAL_APPROVAL=false
```

Then run:

```bash
python -m app.main --limit 10 --execute
```

Keep `REQUIRE_MANUAL_APPROVAL=true` for the manual approval phase. With that default, the bot prints signals and blocks orders.

## Risk Rules

- Max trade size defaults to `$25`.
- Max daily loss defaults to `$20`.
- Max open positions defaults to `3`.
- Stop after `2` losing trades in a day.
- No margin.
- No short selling.
- Sell signals are recommendations only in this first version.

## Test

```bash
pytest
```

## Next Phases

1. Add SQLite persistence for announcements, signals, risk decisions, and paper fills.
2. Add a backtesting module that replays historical announcements against ETF prices.
3. Add a manual approval interface before real-money trading.
4. Add richer NLP and source credibility scoring.
5. Add Docker and deployment only after the paper system is stable.
