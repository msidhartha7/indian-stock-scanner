from __future__ import annotations

from datetime import date

from .models import CatalystSentiment, CompanySnapshot, ScoredCompany


MAX_STALE_DAYS = 14
MIN_AVG_DAILY_VALUE = 1_000_000.0


def _clamp(value: float, floor: float = 0.0, ceiling: float = 1.0) -> float:
    return max(floor, min(ceiling, value))


def _news_weight(item, as_of: date) -> float:
    age = (as_of - item.published_at.date()).days
    if age <= 7:
        return 1.0
    if age <= 30:
        return 0.5
    return 0.1


def score_company(company: CompanySnapshot, *, as_of: date) -> ScoredCompany:
    latest = company.latest
    age_days = (as_of - company.updated_at.date()).days
    rejection_reasons: list[str] = []
    positives: list[str] = []
    risks: list[str] = []

    if age_days > MAX_STALE_DAYS:
        rejection_reasons.append("Data is stale")
    if latest.net_profit <= 0 or company.trailing_twelve_month_profit <= 0:
        rejection_reasons.append("Profitability hard gate failed")
    if latest.revenue_qoq_growth < -0.05:
        rejection_reasons.append("Revenue is declining sharply")
    if company.avg_daily_value < MIN_AVG_DAILY_VALUE:
        rejection_reasons.append("Liquidity is too low")

    growth_inputs = [
        _clamp(latest.revenue_yoy_growth / 0.25),
        _clamp(latest.profit_yoy_growth / 0.25),
        _clamp(latest.revenue_qoq_growth / 0.10),
        _clamp(latest.profit_qoq_growth / 0.10),
        _clamp(latest.margin_delta / 0.05),
    ]
    growth_score = sum(growth_inputs) / len(growth_inputs)
    if growth_score >= 0.75:
        positives.append("Strong earnings momentum")
    elif growth_score < 0.45:
        risks.append("Momentum is below the preferred threshold")

    positive_news = sum(1 for item in company.news if item.sentiment is CatalystSentiment.POSITIVE)
    negative_news = sum(1 for item in company.news if item.sentiment is CatalystSentiment.NEGATIVE)
    positive_score = sum(_news_weight(i, as_of) for i in company.news if i.sentiment is CatalystSentiment.POSITIVE)
    negative_score = sum(_news_weight(i, as_of) for i in company.news if i.sentiment is CatalystSentiment.NEGATIVE)
    catalyst_strength = _clamp((positive_score * 0.28) - (negative_score * 0.18))
    if catalyst_strength >= 0.45:
        positives.append("Fresh catalyst support is visible")
    elif catalyst_strength < 0.2:
        risks.append("Catalyst support is limited")

    setup_quality = 0.0
    if company.last_price > company.sma_50 > company.sma_200:
        setup_quality += 0.45
        positives.append("Price trend is constructive")
    elif company.last_price < company.sma_50:
        risks.append("Price trend needs confirmation")
    setup_quality += _clamp(company.relative_strength_3m / 0.25) * 0.35
    if company.distance_from_52w_high_pct >= -0.10:
        setup_quality += 0.20
        positives.append("Price near 52-week high")
    elif company.distance_from_52w_high_pct <= -0.30:
        setup_quality += 0.05
        risks.append("Price far from 52-week high")
    else:
        setup_quality += 0.12
    setup_quality = _clamp(setup_quality)

    valuation_headroom = _clamp(1.0 - company.valuation_percentile)
    if company.valuation_percentile >= 0.90:
        risks.append("Valuation looks stretched")
    elif company.valuation_percentile <= 0.60:
        positives.append("Valuation still has room to rerate")

    cash_conversion = 1.0 if latest.net_profit <= 0 else latest.operating_cash_flow / latest.net_profit
    debt_pressure = 0.0 if latest.net_profit <= 0 else latest.total_debt / max(latest.net_profit * 4, 1.0)
    risk_score = 0.75
    if cash_conversion < 0.8:
        risk_score -= 0.15
        risks.append("Cash conversion is weak")
    if debt_pressure > 1.0:
        risk_score -= 0.10
        risks.append("Debt is high relative to profits")
    if negative_news:
        risk_score -= min(0.3, negative_news * 0.18)
        risks.append("Governance or balance-sheet risk in recent news")
    risk_score = _clamp(risk_score)

    time_window_fit = _clamp((growth_score * 0.55) + (catalyst_strength * 0.45))
    opportunity_raw = (
        (growth_score * 0.25)
        + (catalyst_strength * 0.20)
        + (setup_quality * 0.20)
        + (valuation_headroom * 0.15)
        + (risk_score * 0.10)
        + (time_window_fit * 0.10)
    )
    opportunity_score = int(round(opportunity_raw * 100))
    passed_hard_gates = not rejection_reasons

    if not passed_hard_gates:
        action_label = "Avoid for now"
    elif company.valuation_percentile >= 0.90 and setup_quality >= 0.70:
        action_label = "Late-entry risk"
    elif opportunity_score >= 67:
        action_label = "Research now"
    elif opportunity_score >= 55:
        action_label = "Watch closely"
    else:
        action_label = "Avoid for now"

    summary = (
        f"{company.ticker} combines {growth_score:.0%} earnings momentum, "
        f"{catalyst_strength:.0%} catalyst strength, and {setup_quality:.0%} setup quality."
    )
    invalidation_reason = (
        "Thesis weakens if momentum fades, the catalyst timeline slips, or valuation expands "
        "without matching earnings follow-through."
    )

    return ScoredCompany(
        ticker=company.ticker,
        company_name=company.company_name,
        sector=company.sector,
        opportunity_score=opportunity_score,
        time_window_fit=time_window_fit,
        catalyst_strength=catalyst_strength,
        valuation_stretch=1.0 - valuation_headroom,
        setup_quality=setup_quality,
        risk_score=risk_score,
        passed_hard_gates=passed_hard_gates,
        action_label=action_label,
        rejection_reasons=rejection_reasons,
        positives=positives,
        risks=risks,
        summary=summary,
        invalidation_reason=invalidation_reason,
        latest=latest,
        last_price=company.last_price,
        updated_at=company.updated_at,
        news=company.news,
    )
