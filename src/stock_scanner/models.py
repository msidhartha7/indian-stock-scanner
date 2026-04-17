from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


class CatalystSentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass(slots=True)
class NewsItem:
    source: str
    title: str
    url: str
    published_at: datetime
    sentiment: CatalystSentiment

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["published_at"] = self.published_at.isoformat()
        data["sentiment"] = self.sentiment.value
        return data


@dataclass(slots=True)
class QuarterlyFinancials:
    quarter: str
    revenue: float
    revenue_prev_year: float
    revenue_prev_quarter: float
    net_profit: float
    profit_prev_year: float
    profit_prev_quarter: float
    operating_margin: float
    operating_margin_prev_quarter: float
    operating_cash_flow: float
    total_debt: float

    @staticmethod
    def _growth(current: float, previous: float) -> float:
        if previous == 0:
            return 0.0
        return (current - previous) / abs(previous)

    @property
    def revenue_yoy_growth(self) -> float:
        return self._growth(self.revenue, self.revenue_prev_year)

    @property
    def revenue_qoq_growth(self) -> float:
        return self._growth(self.revenue, self.revenue_prev_quarter)

    @property
    def profit_yoy_growth(self) -> float:
        return self._growth(self.net_profit, self.profit_prev_year)

    @property
    def profit_qoq_growth(self) -> float:
        return self._growth(self.net_profit, self.profit_prev_quarter)

    @property
    def margin_delta(self) -> float:
        return self.operating_margin - self.operating_margin_prev_quarter

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CompanySnapshot:
    ticker: str
    company_name: str
    sector: str
    latest: QuarterlyFinancials
    trailing_twelve_month_profit: float
    last_price: float
    sma_50: float
    sma_200: float
    distance_from_52w_high_pct: float
    valuation_percentile: float
    relative_strength_3m: float
    avg_daily_value: float
    updated_at: datetime
    news: list[NewsItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "sector": self.sector,
            "latest": self.latest.to_dict(),
            "trailing_twelve_month_profit": self.trailing_twelve_month_profit,
            "last_price": self.last_price,
            "sma_50": self.sma_50,
            "sma_200": self.sma_200,
            "distance_from_52w_high_pct": self.distance_from_52w_high_pct,
            "valuation_percentile": self.valuation_percentile,
            "relative_strength_3m": self.relative_strength_3m,
            "avg_daily_value": self.avg_daily_value,
            "updated_at": self.updated_at.isoformat(),
            "news": [item.to_dict() for item in self.news],
        }


@dataclass(slots=True)
class ScoredCompany:
    ticker: str
    company_name: str
    sector: str
    opportunity_score: int
    time_window_fit: float
    catalyst_strength: float
    valuation_stretch: float
    setup_quality: float
    risk_score: float
    passed_hard_gates: bool
    action_label: str
    rejection_reasons: list[str]
    positives: list[str]
    risks: list[str]
    summary: str
    invalidation_reason: str
    latest: QuarterlyFinancials
    last_price: float
    updated_at: datetime
    news: list[NewsItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "sector": self.sector,
            "opportunity_score": self.opportunity_score,
            "time_window_fit": round(self.time_window_fit, 3),
            "catalyst_strength": round(self.catalyst_strength, 3),
            "valuation_stretch": round(self.valuation_stretch, 3),
            "setup_quality": round(self.setup_quality, 3),
            "risk_score": round(self.risk_score, 3),
            "passed_hard_gates": self.passed_hard_gates,
            "action_label": self.action_label,
            "rejection_reasons": self.rejection_reasons,
            "positives": self.positives,
            "risks": self.risks,
            "summary": self.summary,
            "invalidation_reason": self.invalidation_reason,
            "latest": self.latest.to_dict(),
            "last_price": self.last_price,
            "updated_at": self.updated_at.isoformat(),
            "news": [item.to_dict() for item in self.news],
        }


@dataclass(slots=True)
class ReportBundle:
    generated_for: date
    top_opportunities: list[ScoredCompany]
    catalyst_watchlist: list[ScoredCompany]
    valuation_stretched: list[ScoredCompany]
    high_growth_lacking_confirmation: list[ScoredCompany]
    avoid_for_now: list[ScoredCompany]
    important_developments: list[NewsItem]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_for": self.generated_for.isoformat(),
            "top_opportunities": [item.to_dict() for item in self.top_opportunities],
            "catalyst_watchlist": [item.to_dict() for item in self.catalyst_watchlist],
            "valuation_stretched": [item.to_dict() for item in self.valuation_stretched],
            "high_growth_lacking_confirmation": [
                item.to_dict() for item in self.high_growth_lacking_confirmation
            ],
            "avoid_for_now": [item.to_dict() for item in self.avoid_for_now],
            "important_developments": [item.to_dict() for item in self.important_developments],
        }

