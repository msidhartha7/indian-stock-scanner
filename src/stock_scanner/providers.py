from __future__ import annotations

import json
import math
import statistics
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from .models import CatalystSentiment, CompanySnapshot, NewsItem, QuarterlyFinancials


USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) IndianStockScanner/1.0"
YAHOO_TIMESERIES_TYPES = (
    "quarterlyTotalRevenue",
    "quarterlyNetIncome",
    "quarterlyOperatingIncome",
    "quarterlyOperatingCashFlow",
    "quarterlyTotalDebt",
    "quarterlyBasicAverageShares",
)


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
    "negative": (
        "pledge", "pledged", "fraud", "probe", "downgrade", "dilution", "sell-off",
        "insider selling", "block deal", "notice", "tax demand", "ED", "SEBI",
        "promoter sale", "regulatory violation", "regulatory action",
    ),
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
        fundamentals = _fetch_json(_yahoo_fundamentals_url(symbol))
        news = fetch_google_news(item["company_name"], ticker)
        return _build_snapshot(item, chart, fundamentals, news)


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


def _build_snapshot(item: dict, chart: dict, fundamentals: dict, news: list[NewsItem]) -> CompanySnapshot:
    chart_result = chart["chart"]["result"][0]
    timestamps = chart_result["timestamp"]
    closes = chart_result["indicators"]["quote"][0]["close"]
    volumes = chart_result["indicators"]["quote"][0]["volume"]
    prices = [price for price in closes if price is not None]
    recent_prices = prices[-50:] if len(prices) >= 50 else prices
    long_prices = prices[-200:] if len(prices) >= 200 else prices
    recent_pairs = [(price, volume) for price, volume in zip(closes[-20:], volumes[-20:]) if price and volume]
    series_map = _timeseries_by_type(fundamentals)

    revenue_series = series_map.get("quarterlyTotalRevenue", [])
    profit_series = series_map.get("quarterlyNetIncome", [])
    operating_income_series = series_map.get("quarterlyOperatingIncome", [])
    cashflow_series = series_map.get("quarterlyOperatingCashFlow", [])
    debt_series = series_map.get("quarterlyTotalDebt", [])
    share_series = series_map.get("quarterlyBasicAverageShares", [])

    latest_revenue_entry = _latest_entry(revenue_series)
    latest_profit_entry = _latest_entry(profit_series)
    latest_date = latest_revenue_entry["as_of_date"]

    prev_quarter_revenue_entry = _previous_entry(revenue_series)
    prev_quarter_profit_entry = _previous_entry(profit_series)
    prev_year_revenue_entry = _year_ago_entry(revenue_series, latest_date)
    prev_year_profit_entry = _year_ago_entry(profit_series, latest_date)

    latest_operating_income_entry = _entry_for_date_or_latest(operating_income_series, latest_date)
    prev_operating_income_entry = _entry_for_date_or_latest(
        operating_income_series, prev_quarter_revenue_entry["as_of_date"]
    )
    latest_cashflow_entry = _entry_for_date_or_latest(cashflow_series, latest_date)
    latest_debt_entry = _entry_for_date_or_latest(debt_series, latest_date)
    latest_share_entry = _entry_for_date_or_latest(share_series, latest_date)

    latest_revenue = latest_revenue_entry["raw"]
    latest_profit = latest_profit_entry["raw"]
    prev_quarter_revenue = prev_quarter_revenue_entry["raw"]
    prev_quarter_profit = prev_quarter_profit_entry["raw"]
    prev_year_revenue = prev_year_revenue_entry["raw"]
    prev_year_profit = prev_year_profit_entry["raw"]

    operating_margin = _ratio(latest_operating_income_entry["raw"], latest_revenue)
    previous_operating_margin = _ratio(prev_operating_income_entry["raw"], prev_quarter_revenue)
    trailing_twelve_month_profit = sum(item["raw"] for item in profit_series[-4:]) if profit_series else 0.0
    share_count = latest_share_entry["raw"]
    trailing_eps = (trailing_twelve_month_profit / share_count) if share_count > 0 else 0.0

    average_daily_value = statistics.mean(price * volume for price, volume in recent_pairs) if recent_pairs else 0.0
    current_price = float(chart_result["meta"].get("regularMarketPrice", prices[-1] if prices else 0.0) or 0.0)
    year_high = float(chart_result["meta"].get("fiftyTwoWeekHigh") or 0) or max(prices, default=current_price)
    distance_from_52w_high_pct = ((current_price / year_high) - 1.0) if year_high else 0.0
    trailing_pe = (current_price / trailing_eps) if trailing_eps > 0 else 0.0
    valuation_percentile = _estimate_valuation_percentile(trailing_pe)

    latest_timestamp = datetime.fromtimestamp(timestamps[-1], tz=timezone.utc)
    earnings_datetime = datetime(latest_date.year, latest_date.month, latest_date.day, tzinfo=timezone.utc)

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
            operating_margin_prev_quarter=previous_operating_margin,
            operating_cash_flow=latest_cashflow_entry["raw"],
            total_debt=latest_debt_entry["raw"],
        ),
        trailing_twelve_month_profit=trailing_twelve_month_profit,
        last_price=current_price,
        sma_50=statistics.mean(recent_prices) if recent_prices else current_price,
        sma_200=statistics.mean(long_prices) if long_prices else current_price,
        distance_from_52w_high_pct=distance_from_52w_high_pct,
        valuation_percentile=valuation_percentile,
        relative_strength_3m=_relative_strength(prices),
        avg_daily_value=average_daily_value,
        updated_at=earnings_datetime,
        news=news,
    )


def _yahoo_fundamentals_url(symbol: str) -> str:
    period2 = int(datetime.now(tz=timezone.utc).timestamp())
    period1 = int((datetime.now(tz=timezone.utc) - timedelta(days=366 * 6)).timestamp())
    query = urllib.parse.urlencode(
        {
            "type": ",".join(YAHOO_TIMESERIES_TYPES),
            "period1": period1,
            "period2": period2,
        }
    )
    return (
        "https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/"
        f"{symbol}?{query}"
    )


def _timeseries_by_type(payload: dict) -> dict[str, list[dict[str, object]]]:
    result = payload.get("timeseries", {}).get("result", [])
    series_map: dict[str, list[dict[str, object]]] = {}
    for item in result:
        series_type = item.get("meta", {}).get("type", [None])[0]
        if not series_type:
            continue
        raw_entries = item.get(series_type, [])
        entries = []
        for raw_entry in raw_entries:
            as_of_date = raw_entry.get("asOfDate")
            if not as_of_date:
                continue
            entries.append(
                {
                    "as_of_date": date.fromisoformat(as_of_date),
                    "raw": float(raw_entry.get("reportedValue", {}).get("raw", 0.0) or 0.0),
                }
            )
        entries.sort(key=lambda value: value["as_of_date"])
        series_map[series_type] = entries
    return series_map


def _latest_entry(entries: list[dict[str, object]]) -> dict[str, object]:
    if not entries:
        return {"as_of_date": date.today(), "raw": 0.0}
    return entries[-1]


def _previous_entry(entries: list[dict[str, object]]) -> dict[str, object]:
    if len(entries) >= 2:
        return entries[-2]
    return _latest_entry(entries)


def _year_ago_entry(entries: list[dict[str, object]], latest_date: date) -> dict[str, object]:
    if not entries:
        return {"as_of_date": latest_date, "raw": 0.0}
    target = latest_date - timedelta(days=365)
    return min(entries, key=lambda entry: abs((entry["as_of_date"] - target).days))


def _entry_for_date_or_latest(entries: list[dict[str, object]], target_date: date) -> dict[str, object]:
    if not entries:
        return {"as_of_date": target_date, "raw": 0.0}
    exact = [entry for entry in entries if entry["as_of_date"] == target_date]
    if exact:
        return exact[-1]
    prior = [entry for entry in entries if entry["as_of_date"] <= target_date]
    if prior:
        return prior[-1]
    return entries[-1]


def _ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _estimate_valuation_percentile(trailing_pe: float) -> float:
    if trailing_pe <= 0:
        return 0.5
    return max(0.1, min(0.98, math.log1p(trailing_pe) / math.log1p(120.0)))


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
