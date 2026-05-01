from __future__ import annotations

from app.config import Settings, settings
from app.models import PortfolioState, RiskDecision, Signal, SignalAction


class RiskManager:
    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    def evaluate(self, signal: Signal, portfolio: PortfolioState) -> RiskDecision:
        reasons: list[str] = []

        if signal.action == SignalAction.HOLD:
            reasons.append("hold signal does not require a trade")

        if signal.action == SignalAction.SELL:
            reasons.append("short selling is disabled; sell signals are recommendations only")

        if portfolio.open_positions >= self.config.max_open_positions:
            reasons.append("max open positions reached")

        if portfolio.daily_realized_loss >= self.config.max_daily_loss_dollars:
            reasons.append("max daily loss reached")

        if portfolio.daily_loss_count >= self.config.max_daily_losses:
            reasons.append("daily loss count limit reached")

        if self.config.require_manual_approval:
            reasons.append("manual approval required before any order")

        approved = not reasons and signal.action == SignalAction.BUY
        trade_dollars = self.config.max_trade_dollars if approved else 0.0
        return RiskDecision(approved=approved, trade_dollars=trade_dollars, reasons=tuple(reasons))

