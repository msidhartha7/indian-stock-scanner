from __future__ import annotations

from datetime import datetime, timezone

from .models import CatalystSentiment, CompanySnapshot, NewsItem, QuarterlyFinancials


def demo_companies() -> list[CompanySnapshot]:
    return [
        CompanySnapshot(
            ticker="TRENT",
            company_name="Trent",
            sector="Retail",
            latest=QuarterlyFinancials(
                quarter="Q4FY26",
                revenue=220.0,
                revenue_prev_year=150.0,
                revenue_prev_quarter=195.0,
                net_profit=46.0,
                profit_prev_year=28.0,
                profit_prev_quarter=40.0,
                operating_margin=0.23,
                operating_margin_prev_quarter=0.20,
                operating_cash_flow=60.0,
                total_debt=10.0,
            ),
            trailing_twelve_month_profit=180.0,
            last_price=100.0,
            sma_50=94.0,
            sma_200=80.0,
            distance_from_52w_high_pct=-0.04,
            valuation_percentile=0.58,
            relative_strength_3m=0.24,
            avg_daily_value=25_000_000.0,
            updated_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
            news=[
                NewsItem(
                    source="Demo Wire",
                    title="Order win and expansion update",
                    url="https://example.com/trent",
                    published_at=datetime(2026, 4, 16, tzinfo=timezone.utc),
                    sentiment=CatalystSentiment.POSITIVE,
                )
            ],
        ),
        CompanySnapshot(
            ticker="CALM",
            company_name="Calm Industries",
            sector="Industrials",
            latest=QuarterlyFinancials(
                quarter="Q4FY26",
                revenue=150.0,
                revenue_prev_year=102.0,
                revenue_prev_quarter=142.0,
                net_profit=30.0,
                profit_prev_year=19.0,
                profit_prev_quarter=28.0,
                operating_margin=0.21,
                operating_margin_prev_quarter=0.20,
                operating_cash_flow=28.0,
                total_debt=18.0,
            ),
            trailing_twelve_month_profit=120.0,
            last_price=88.0,
            sma_50=86.0,
            sma_200=79.0,
            distance_from_52w_high_pct=-0.08,
            valuation_percentile=0.62,
            relative_strength_3m=0.10,
            avg_daily_value=7_500_000.0,
            updated_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
            news=[],
        ),
    ]

