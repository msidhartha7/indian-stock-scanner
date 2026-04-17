from __future__ import annotations

from .models import ReportBundle, ScoredCompany


def render_markdown_report(bundle: ReportBundle) -> str:
    sections = [
        f"# Indian Stock Opportunity Scan - {bundle.generated_for.isoformat()}",
        "",
        "## Top 10 3-6 month opportunities",
        _render_company_section(bundle.top_opportunities, empty_text="No top opportunities today."),
        "",
        "## Catalyst-driven watchlist",
        _render_company_section(bundle.catalyst_watchlist, empty_text="No watchlist names today."),
        "",
        "## Late-entry risk — wait for a pullback",
        _render_company_section(bundle.late_entry_risk, empty_text="No late-entry risk names today."),
        "",
        "## Valuation-stretched names to avoid",
        _render_company_section(bundle.valuation_stretched, empty_text="No valuation warnings today."),
        "",
        "## High-growth names lacking confirmation",
        _render_company_section(
            bundle.high_growth_lacking_confirmation,
            empty_text="No unconfirmed high-growth names today.",
        ),
        "",
        "## Avoid for now",
        _render_company_section(bundle.avoid_for_now, empty_text="No avoid-for-now names today."),
        "",
        "## Important new developments since previous scan",
        _render_news_section(bundle),
    ]
    return "\n".join(sections).strip() + "\n"


def _render_company_section(companies: list[ScoredCompany], *, empty_text: str) -> str:
    if not companies:
        return empty_text
    rows: list[str] = []
    for company in companies:
        growth = company.latest
        rows.extend(
            [
                f"### {company.ticker} - {company.company_name}",
                f"- Opportunity score: {company.opportunity_score} ({company.action_label})",
                f"- Revenue growth: {growth.revenue_yoy_growth:.1%} YoY, {growth.revenue_qoq_growth:.1%} QoQ",
                f"- Profit growth: {growth.profit_yoy_growth:.1%} YoY, {growth.profit_qoq_growth:.1%} QoQ",
                f"- Setup quality: {company.setup_quality:.0%}",
                f"- Catalyst strength: {company.catalyst_strength:.0%}",
                f"- Valuation stretch: {company.valuation_stretch:.0%}",
                f"- Positives: {', '.join(company.positives) if company.positives else 'None'}",
                f"- Risks: {', '.join(company.risks) if company.risks else 'None'}",
                f"- Why it may work: {company.summary}",
                f"- What invalidates it: {company.invalidation_reason}",
                "",
            ]
        )
    return "\n".join(rows).strip()


def _render_news_section(bundle: ReportBundle) -> str:
    if not bundle.important_developments:
        return "No notable new developments today."
    rows = []
    for item in bundle.important_developments:
        rows.append(
            f"- {item.published_at.date().isoformat()} [{item.source}] {item.title} ({item.sentiment.value}) - {item.url}"
        )
    return "\n".join(rows)

