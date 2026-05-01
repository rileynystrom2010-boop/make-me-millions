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

    def check_connection(self) -> str:
        if not self.config.alpaca_api_key or not self.config.alpaca_secret_key:
            return "Alpaca keys are missing. Add ALPACA_API_KEY and ALPACA_SECRET_KEY to .env."
        if not self.config.alpaca_paper:
            return "Blocked: ALPACA_PAPER must be true for this bot stage."

        account = self._get_client().get_account()
        return (
            "Alpaca paper account connected: "
            f"status={account.status}, "
            f"buying_power={account.buying_power}, "
            f"cash={account.cash}, "
            f"trading_blocked={account.trading_blocked}"
        )

    def submit_fractional_order(self, signal: Signal, risk: RiskDecision) -> str:
        if not self.enabled():
            return "dry-run: Alpaca paper trading is not enabled"
        if not risk.approved:
            return f"blocked by risk manager: {'; '.join(risk.reasons)}"
        if signal.action != SignalAction.BUY:
            return f"blocked: only buy orders are supported, got {signal.action.value}"

        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        order_request = MarketOrderRequest(
            symbol=signal.ticker,
            notional=risk.trade_dollars,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
        )
        order = self._get_client().submit_order(order_request)
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
