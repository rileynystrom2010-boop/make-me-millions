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
  database.py
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

Each run is logged to SQLite by default at `data/trading_bot.sqlite3`. Use `--no-log` for a temporary run that should not be saved.

If one source is slow, skip it or lower the timeout:

```bash
python -m app.main --limit 10 --skip-federal-register
python -m app.main --limit 10 --timeout 3
```

## Connect Alpaca Paper

After you add paper keys to `.env`, validate the account connection:

```bash
python -m app.main --check-alpaca
```

Keep these settings while you are first testing:

```env
ALPACA_PAPER=true
ALPACA_ENABLE_TRADING=false
REQUIRE_MANUAL_APPROVAL=true
MAX_TRADE_DOLLARS=10
```

That configuration confirms keys and collects signals while still blocking orders.

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

Keep `REQUIRE_MANUAL_APPROVAL=true` for the manual approval phase. With that default, the bot prints signals, logs the decision, and blocks orders.

## Audit Trail

The SQLite database stores:

- collected news items
- generated signals
- risk decisions
- dry-run, blocked, or submitted execution messages

This gives you a record to review before increasing risk or enabling paper execution.

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

1. Add a backtesting module that replays historical announcements against ETF prices.
2. Add a manual approval interface before real-money trading.
3. Add richer NLP and source credibility scoring.
4. Add Docker and deployment only after the paper system is stable.
