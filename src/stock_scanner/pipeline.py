from __future__ import annotations

from datetime import date

from .models import CompanySnapshot, NewsItem, ReportBundle
from .scoring import score_company


def build_report_bundle(companies: list[CompanySnapshot], *, as_of: date) -> ReportBundle:
    scored = sorted(
        (score_company(company, as_of=as_of) for company in companies),
        key=lambda item: item.opportunity_score,
        reverse=True,
    )

    top_opportunities = [
        item for item in scored if item.action_label == "Research now" and item.passed_hard_gates
    ][:10]
    catalyst_watchlist = [item for item in scored if item.action_label == "Watch closely"][:10]
    late_entry_risk = [item for item in scored if item.action_label == "Late-entry risk"][:10]
    valuation_stretched = [
        item for item in scored
        if "Valuation looks stretched" in item.risks and item.passed_hard_gates
    ][:10]
    high_growth_lacking_confirmation = [
        item
        for item in scored
        if "Strong earnings momentum" in item.positives and item.action_label != "Research now"
    ][:10]
    avoid_for_now = [item for item in scored if item.action_label == "Avoid for now"][:10]

    important_developments = _top_developments(scored)
    return ReportBundle(
        generated_for=as_of,
        top_opportunities=top_opportunities,
        catalyst_watchlist=catalyst_watchlist,
        late_entry_risk=late_entry_risk,
        valuation_stretched=valuation_stretched,
        high_growth_lacking_confirmation=high_growth_lacking_confirmation,
        avoid_for_now=avoid_for_now,
        important_developments=important_developments,
    )


def _top_developments(scored_companies) -> list[NewsItem]:
    news_items: list[NewsItem] = []
    seen: set[str] = set()
    for company in scored_companies:
        for item in sorted(company.news, key=lambda news: news.published_at, reverse=True):
            if item.url in seen:
                continue
            seen.add(item.url)
            news_items.append(item)
            if len(news_items) == 10:
                return news_items
    return news_items

