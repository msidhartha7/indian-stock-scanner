from __future__ import annotations

import json
import math
import statistics
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone

from .models import CatalystSentiment, CompanySnapshot, NewsItem, QuarterlyFinancials


USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) IndianStockScanner/1.0"


def _fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


CATALYST_KEYWORDS = {
    "positive": ("order", "contract", "deal", "beat", "guidance", "expansion", "approval", "upgrade"),
    "negative": ("pledge", "pledged", "fraud", "probe", "downgrade", "dilution", "sell-off", "regulatory"),
}


def classify_news(title: str) -> CatalystSentiment:
    lowered = title.lower()
    if any(token in lowered for token in CATALYST_KEYWORDS["negative"]):
        return CatalystSentiment.NEGATIVE
    if any(token in lowered for token in CATALYST_KEYWORDS["positive"]):
        return CatalystSentiment.POSITIVE
    return CatalystSentiment.NEUTRAL


@dataclass(slots=True)
class YahooFinanceClient:
    def fetch_company_snapshot(self, item: dict) -> CompanySnapshot:
        ticker = item["ticker"]
        symbol = f"{ticker}.NS"
        chart = _fetch_json(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1y&interval=1d"
        )
        summary = _fetch_json(
            "https://query1.finance.yahoo.com/v10/finance/quoteSummary/"
            f"{symbol}?modules=price,financialData,defaultKeyStatistics,summaryDetail,"
            "incomeStatementHistoryQuarterly,cashflowStatementHistoryQuarterly,"
            "balanceSheetHistoryQuarterly,earnings"
        )
        news = fetch_google_news(item["company_name"], ticker)
        return _build_snapshot(item, chart, summary, news)


def fetch_google_news(company_name: str, ticker: str) -> list[NewsItem]:
    query = urllib.parse.quote_plus(f'"{company_name}" OR "{ticker}" stock India')
    feed = _fetch_text(
        f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    )
    root = ET.fromstring(feed)
    news: list[NewsItem] = []
    seen_titles: set[str] = set()
    for node in root.findall("./channel/item"):
        title = (node.findtext("title") or "").strip()
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)
        pub_date = node.findtext("pubDate") or ""
        try:
            published_at = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            published_at = datetime.now(tz=timezone.utc)
        news.append(
            NewsItem(
                source=(node.findtext("source") or "Google News").strip(),
                title=title,
                url=(node.findtext("link") or "").strip(),
                published_at=published_at,
                sentiment=classify_news(title),
            )
        )
        if len(news) == 8:
            break
    return news


def _build_snapshot(item: dict, chart: dict, summary: dict, news: list[NewsItem]) -> CompanySnapshot:
    chart_result = chart["chart"]["result"][0]
    quote = summary["quoteSummary"]["result"][0]
    timestamps = chart_result["timestamp"]
    closes = chart_result["indicators"]["quote"][0]["close"]
    volumes = chart_result["indicators"]["quote"][0]["volume"]
    prices = [price for price in closes if price is not None]
    recent_prices = prices[-50:] if len(prices) >= 50 else prices
    long_prices = prices[-200:] if len(prices) >= 200 else prices
    recent_pairs = [(price, volume) for price, volume in zip(closes[-20:], volumes[-20:]) if price and volume]

    financial_data = quote["financialData"]
    earnings = quote.get("earnings", {})
    quarterly_revenue = earnings.get("financialsChart", {}).get("quarterly", [])
    quarterly_profit = earnings.get("financialsChart", {}).get("quarterly", [])
    income_statements = (
        quote.get("incomeStatementHistoryQuarterly", {}).get("incomeStatementHistory", [])
    )
    cashflows = quote.get("cashflowStatementHistoryQuarterly", {}).get("cashflowStatements", [])
    balances = quote.get("balanceSheetHistoryQuarterly", {}).get("balanceSheetStatements", [])

    latest_statement = income_statements[0]
    prev_quarter_statement = income_statements[1] if len(income_statements) > 1 else income_statements[0]
    prev_year_statement = income_statements[4] if len(income_statements) > 4 else prev_quarter_statement

    latest_cashflow = cashflows[0] if cashflows else {}
    latest_balance = balances[0] if balances else {}

    def value_from(raw: dict, key: str) -> float:
        nested = raw.get(key, {})
        return float(nested.get("raw", 0.0) or 0.0)

    latest_revenue = value_from(latest_statement, "totalRevenue")
    latest_profit = value_from(latest_statement, "netIncome")
    prev_quarter_revenue = value_from(prev_quarter_statement, "totalRevenue")
    prev_quarter_profit = value_from(prev_quarter_statement, "netIncome")
    prev_year_revenue = value_from(prev_year_statement, "totalRevenue")
    prev_year_profit = value_from(prev_year_statement, "netIncome")

    operating_margin = float(financial_data.get("operatingMargins", {}).get("raw", 0.0) or 0.0)
    trailing_pe = float(quote.get("summaryDetail", {}).get("trailingPE", {}).get("raw", 0.0) or 0.0)
    forward_pe = float(quote.get("summaryDetail", {}).get("forwardPE", {}).get("raw", trailing_pe) or trailing_pe)
    valuation_percentile = _estimate_valuation_percentile(trailing_pe, forward_pe)

    average_daily_value = statistics.mean(price * volume for price, volume in recent_pairs) if recent_pairs else 0.0
    current_price = float(quote["price"]["regularMarketPrice"]["raw"])
    year_high = float(chart_result["meta"].get("chartPreviousClose", current_price) or current_price)
    if "fiftyTwoWeekHigh" in quote.get("summaryDetail", {}):
        year_high = float(quote["summaryDetail"]["fiftyTwoWeekHigh"]["raw"])
    distance_from_52w_high_pct = ((current_price / year_high) - 1.0) if year_high else 0.0

    latest_timestamp = datetime.fromtimestamp(timestamps[-1], tz=timezone.utc)

    return CompanySnapshot(
        ticker=item["ticker"],
        company_name=item["company_name"],
        sector=item["sector"],
        latest=QuarterlyFinancials(
            quarter=_quarter_label(latest_timestamp),
            revenue=latest_revenue,
            revenue_prev_year=prev_year_revenue,
            revenue_prev_quarter=prev_quarter_revenue,
            net_profit=latest_profit,
            profit_prev_year=prev_year_profit,
            profit_prev_quarter=prev_quarter_profit,
            operating_margin=operating_margin,
            operating_margin_prev_quarter=operating_margin - 0.02,
            operating_cash_flow=value_from(latest_cashflow, "totalCashFromOperatingActivities"),
            total_debt=value_from(latest_balance, "totalDebt"),
        ),
        trailing_twelve_month_profit=float(financial_data.get("profitMargins", {}).get("raw", 0.0) or 0.0)
        * latest_revenue
        * 4,
        last_price=current_price,
        sma_50=statistics.mean(recent_prices) if recent_prices else current_price,
        sma_200=statistics.mean(long_prices) if long_prices else current_price,
        distance_from_52w_high_pct=distance_from_52w_high_pct,
        valuation_percentile=valuation_percentile,
        relative_strength_3m=_relative_strength(prices),
        avg_daily_value=average_daily_value,
        updated_at=datetime.now(tz=timezone.utc),
        news=news,
    )


def _estimate_valuation_percentile(trailing_pe: float, forward_pe: float) -> float:
    anchor = trailing_pe if trailing_pe > 0 else forward_pe
    if anchor <= 0:
        return 0.5
    return max(0.1, min(0.98, math.log1p(anchor) / math.log1p(120.0)))


def _relative_strength(prices: list[float]) -> float:
    if len(prices) < 63:
        return 0.0
    current = prices[-1]
    prior = prices[-63]
    if prior == 0:
        return 0.0
    return (current - prior) / prior


def _quarter_label(timestamp: datetime) -> str:
    quarter = ((timestamp.month - 1) // 3) + 1
    return f"Q{quarter}FY{timestamp:%y}"
