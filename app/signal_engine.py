from __future__ import annotations

from dataclasses import dataclass

from app.models import Classification, NewsItem, Signal, SignalAction


SECTOR_RULES: dict[str, dict[str, tuple[str, ...]]] = {
    "energy": {
        "keywords": ("oil", "gas", "drilling", "pipeline", "opec", "lng", "energy"),
        "tickers": ("XLE",),
    },
    "semiconductors": {
        "keywords": ("semiconductor", "chip", "chips", "ai chip", "export controls", "advanced computing"),
        "tickers": ("SOXX", "SMH"),
    },
    "industrials_materials": {
        "keywords": ("tariff", "tariffs", "steel", "aluminum", "manufacturing", "imports", "duties"),
        "tickers": ("XLI", "XLB"),
    },
    "pharma_healthcare": {
        "keywords": ("pharma", "drug pricing", "medicare", "fda", "vaccine", "healthcare"),
        "tickers": ("XLV",),
    },
    "financials": {
        "keywords": ("bank", "banks", "capital requirements", "interest rates", "treasury", "financial regulation"),
        "tickers": ("XLF",),
    },
    "broad_market": {
        "keywords": ("sanctions", "shutdown", "debt ceiling", "emergency", "executive order"),
        "tickers": ("SPY",),
    },
}

NEGATIVE_TERMS = ("ban", "restrict", "restriction", "sanction", "penalty", "investigation", "tariff")
POSITIVE_TERMS = ("approve", "approval", "permit", "subsidy", "tax credit", "deregulation", "exemption")


@dataclass(frozen=True)
class SignalEngine:
    min_confidence: float = 0.35

    def classify(self, item: NewsItem) -> Classification | None:
        text = item.text.lower()
        best_sector = ""
        best_keywords: tuple[str, ...] = ()
        best_tickers: tuple[str, ...] = ()

        for sector, rule in SECTOR_RULES.items():
            matches = tuple(keyword for keyword in rule["keywords"] if keyword in text)
            if len(matches) > len(best_keywords):
                best_sector = sector
                best_keywords = matches
                best_tickers = rule["tickers"]

        if not best_sector:
            return None

        confidence = min(0.95, 0.25 + (0.18 * len(best_keywords)))
        return Classification(
            sector=best_sector,
            keywords=best_keywords,
            tickers=best_tickers,
            confidence=confidence,
            rationale=f"matched keywords: {', '.join(best_keywords)}",
        )

    def generate_signal(self, item: NewsItem) -> Signal:
        classification = self.classify(item)
        if classification is None or classification.confidence < self.min_confidence:
            return Signal(
                action=SignalAction.HOLD,
                ticker="CASH",
                sector="unknown",
                confidence=0.0,
                reason="no high-confidence sector match",
                source_url=item.url,
            )

        action = self._choose_action(item)
        ticker = classification.tickers[0] if action != SignalAction.HOLD else "CASH"
        return Signal(
            action=action,
            ticker=ticker,
            sector=classification.sector,
            confidence=classification.confidence,
            reason=classification.rationale,
            source_url=item.url,
        )

    def _choose_action(self, item: NewsItem) -> SignalAction:
        text = item.text.lower()
        negative_hits = sum(1 for term in NEGATIVE_TERMS if term in text)
        positive_hits = sum(1 for term in POSITIVE_TERMS if term in text)

        if negative_hits > positive_hits:
            return SignalAction.SELL
        if positive_hits > negative_hits:
            return SignalAction.BUY
        return SignalAction.HOLD

