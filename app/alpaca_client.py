from __future__ import annotations

from app.config import Settings, settings
from app.models import RiskDecision, Signal, SignalAction


class AlpacaPaperClient:
    """Thin Alpaca wrapper with paper-first guardrails."""

    def __init__(self, config: Settings = settings) -> None:
        self.config = config
        self._client = None

    def enabled(self) -> bool:
        return bool(
            self.config.alpaca_api_key
            and self.config.alpaca_secret_key
            and self.config.alpaca_paper
            and self.config.alpaca_enable_trading
        )

    def submit_fractional_order(self, signal: Signal, risk: RiskDecision) -> str:
        if not self.enabled():
            return "dry-run: Alpaca paper trading is not enabled"
        if not risk.approved:
            return f"blocked by risk manager: {'; '.join(risk.reasons)}"
        if signal.action != SignalAction.BUY:
            return f"blocked: only buy orders are supported, got {signal.action.value}"

        client = self._get_client()
        order = client.submit_order(
            symbol=signal.ticker,
            notional=risk.trade_dollars,
            side="buy",
            type="market",
            time_in_force="day",
        )
        return f"paper order submitted: {order.id}"

    def _get_client(self):
        if self._client is None:
            from alpaca.trading.client import TradingClient

            self._client = TradingClient(
                api_key=self.config.alpaca_api_key,
                secret_key=self.config.alpaca_secret_key,
                paper=True,
            )
        return self._client

