# Scoring Strategy Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix four code bugs and apply six strategy improvements to the stock scoring, pipeline, and reporting layers.

**Architecture:** Changes are confined to five source files (`providers.py`, `scoring.py`, `pipeline.py`, `models.py`, `reporting.py`) and one support file (`frontend_data.py`). All tests live in `tests/test_scanner.py`. Group A fixes providers.py; Group B fixes scoring.py; Group C extends the pipeline/model/reporting layer.

**Tech Stack:** Python 3.12 stdlib only. Tests via `unittest`. Run with `PYTHONPATH=src python3 -m unittest discover -s tests -v`.

---

## File Map

| File | What changes |
|------|-------------|
| `src/stock_scanner/providers.py` | Bug 1 (valuation arg), Bug 2 (year_high fallback), Bug 3 (updated_at), Fix 8 (keywords) |
| `src/stock_scanner/scoring.py` | Bug 4 (52w logic), Fix 5 (news recency), Fix 6 (YoY ceiling), Fix 7 (time_window_fit weight) |
| `src/stock_scanner/pipeline.py` | Fix 9 (hard-gate filter), Fix 10 (late_entry_risk bucket) |
| `src/stock_scanner/models.py` | Fix 10 (new ReportBundle field) |
| `src/stock_scanner/reporting.py` | Fix 10 (new markdown section) |
| `src/stock_scanner/frontend_data.py` | Fix 10 (new bucketCounts key) |
| `tests/test_scanner.py` | New and updated tests throughout |

---

## Group A: Provider Bug Fixes

### Task 1: Fix Bug 3 — `updated_at` tracks earnings date, not price date

**Files:**
- Modify: `src/stock_scanner/providers.py` (around line 157)
- Test: `tests/test_scanner.py` — add assertion to `test_yahoo_client_uses_fundamentals_timeseries_endpoint_for_live_snapshot`

- [ ] **Step 1: Write a failing assertion**

In `tests/test_scanner.py`, at the end of `test_yahoo_client_uses_fundamentals_timeseries_endpoint_for_live_snapshot` (after line 525), add:

```python
        # updated_at must reflect the latest earnings date (2025-03-31), not the chart timestamp
        from datetime import date
        self.assertEqual(snapshot.updated_at.date(), date(2025, 3, 31))
```

- [ ] **Step 2: Run to confirm it fails**

```bash
PYTHONPATH=src python3 -m unittest tests.test_scanner.ProviderTests.test_yahoo_client_uses_fundamentals_timeseries_endpoint_for_live_snapshot -v
```

Expected: FAIL — `updated_at.date()` is `2025-04-01` (last chart timestamp), not `2025-03-31`.

- [ ] **Step 3: Fix `_build_snapshot` in `providers.py`**

After line 156 (`latest_timestamp = datetime.fromtimestamp(timestamps[-1], tz=timezone.utc)`), add:

```python
    earnings_datetime = datetime(latest_date.year, latest_date.month, latest_date.day, tzinfo=timezone.utc)
```

On line 184 inside `return CompanySnapshot(...)`, change:

```python
        updated_at=latest_timestamp,
```

to:

```python
        updated_at=earnings_datetime,
```

(`latest_timestamp` is still used for `_quarter_label` on line 163 — leave that call unchanged.)

- [ ] **Step 4: Run test to confirm it passes**

```bash
PYTHONPATH=src python3 -m unittest tests.test_scanner.ProviderTests.test_yahoo_client_uses_fundamentals_timeseries_endpoint_for_live_snapshot -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stock_scanner/providers.py tests/test_scanner.py
git commit -m "fix: updated_at now tracks earnings report date not last price date"
```

---

### Task 2: Fix Bug 2 — `year_high` wrong fallback when `fiftyTwoWeekHigh` absent

**Files:**
- Modify: `src/stock_scanner/providers.py` (lines 150-153)
- Test: `tests/test_scanner.py` — add new test

- [ ] **Step 1: Write a failing test**

Add a new test class method inside `ProviderTests`:

```python
    def test_year_high_falls_back_to_max_price_when_meta_field_absent(self) -> None:
        from stock_scanner import providers

        # Prices declining from 2600 to 2450 — no fiftyTwoWeekHigh in meta
        chart_payload = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "regularMarketPrice": 2450.0,
                            # deliberately no fiftyTwoWeekHigh
                        },
                        "timestamp": [1719792000, 1743465600],
                        "indicators": {
                            "quote": [
                                {
                                    "close": [2600.0, 2450.0],
                                    "volume": [1000000, 1000000],
                                }
                            ]
                        },
                    }
                ]
            }
        }
        timeseries_payload = {
            "timeseries": {
                "result": [
                    {
                        "meta": {"symbol": ["TEST.NS"], "type": ["quarterlyTotalRevenue"]},
                        "quarterlyTotalRevenue": [
                            {"asOfDate": "2024-06-30", "reportedValue": {"raw": 1000.0}},
                            {"asOfDate": "2024-09-30", "reportedValue": {"raw": 1050.0}},
                            {"asOfDate": "2024-12-31", "reportedValue": {"raw": 1100.0}},
                            {"asOfDate": "2025-03-31", "reportedValue": {"raw": 1200.0}},
                        ],
                    },
                    {
                        "meta": {"symbol": ["TEST.NS"], "type": ["quarterlyNetIncome"]},
                        "quarterlyNetIncome": [
                            {"asOfDate": "2024-06-30", "reportedValue": {"raw": 100.0}},
                            {"asOfDate": "2024-09-30", "reportedValue": {"raw": 110.0}},
                            {"asOfDate": "2024-12-31", "reportedValue": {"raw": 120.0}},
                            {"asOfDate": "2025-03-31", "reportedValue": {"raw": 130.0}},
                        ],
                    },
                    {
                        "meta": {"symbol": ["TEST.NS"], "type": ["quarterlyOperatingIncome"]},
                        "quarterlyOperatingIncome": [
                            {"asOfDate": "2025-03-31", "reportedValue": {"raw": 150.0}},
                        ],
                    },
                    {
                        "meta": {"symbol": ["TEST.NS"], "type": ["quarterlyOperatingCashFlow"]},
                        "quarterlyOperatingCashFlow": [
                            {"asOfDate": "2025-03-31", "reportedValue": {"raw": 120.0}},
                        ],
                    },
                    {
                        "meta": {"symbol": ["TEST.NS"], "type": ["quarterlyTotalDebt"]},
                        "quarterlyTotalDebt": [
                            {"asOfDate": "2025-03-31", "reportedValue": {"raw": 50.0}},
                        ],
                    },
                    {
                        "meta": {"symbol": ["TEST.NS"], "type": ["quarterlyBasicAverageShares"]},
                        "quarterlyBasicAverageShares": [
                            {"asOfDate": "2025-03-31", "reportedValue": {"raw": 10.0}},
                        ],
                    },
                ],
                "error": None,
            }
        }

        def fake_fetch(url: str) -> dict:
            if "finance/chart" in url:
                return chart_payload
            return timeseries_payload

        with patch.object(providers, "_fetch_json", side_effect=fake_fetch), patch.object(
            providers, "fetch_google_news", return_value=[]
        ):
            snapshot = providers.YahooFinanceClient().fetch_company_snapshot(
                {"ticker": "TEST", "company_name": "Test Co", "sector": "IT"}
            )

        # year_high must come from max(prices) = 2600, not from chartPreviousClose
        self.assertAlmostEqual(snapshot.distance_from_52w_high_pct, (2450 / 2600) - 1, places=4)
```

- [ ] **Step 2: Run to confirm it fails**

```bash
PYTHONPATH=src python3 -m unittest tests.test_scanner.ProviderTests.test_year_high_falls_back_to_max_price_when_meta_field_absent -v
```

Expected: FAIL — distance will be `0.0` (current_price == chartPreviousClose fallback ≈ current_price).

- [ ] **Step 3: Fix `_build_snapshot` in `providers.py`**

Replace lines 150-153:

```python
    year_high = float(chart_result["meta"].get("chartPreviousClose", current_price) or current_price)
    if "fiftyTwoWeekHigh" in chart_result["meta"]:
        year_high = float(chart_result["meta"]["fiftyTwoWeekHigh"] or year_high)
```

with:

```python
    year_high = float(chart_result["meta"].get("fiftyTwoWeekHigh") or 0) or max(prices, default=current_price)
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
PYTHONPATH=src python3 -m unittest tests.test_scanner.ProviderTests.test_year_high_falls_back_to_max_price_when_meta_field_absent -v
```

Expected: PASS

- [ ] **Step 5: Run full suite**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/stock_scanner/providers.py tests/test_scanner.py
git commit -m "fix: use max(prices) as fallback for 52-week high when meta field absent"
```

---

### Task 3: Fix Bug 1 + Fix 8 — valuation duplicate arg and keyword expansion

**Files:**
- Modify: `src/stock_scanner/providers.py` (lines 38-50, 155, 266-270)
- Test: `tests/test_scanner.py` — add keyword classification test

- [ ] **Step 1: Write failing keyword tests**

Add inside `ProviderTests`:

```python
    def test_classify_news_detects_new_negative_keywords(self) -> None:
        from stock_scanner.providers import classify_news
        from stock_scanner.models import CatalystSentiment

        cases = [
            "Promoter sale triggers block deal in mid-cap stock",
            "SEBI issues notice to board members",
            "ED probe into tax demand from FY23",
            "Regulatory action taken against management",
            "Insider selling detected ahead of results",
        ]
        for title in cases:
            with self.subTest(title=title):
                self.assertEqual(classify_news(title), CatalystSentiment.NEGATIVE, msg=title)

    def test_classify_news_does_not_flag_generic_regulatory_as_negative(self) -> None:
        from stock_scanner.providers import classify_news
        from stock_scanner.models import CatalystSentiment

        # "regulatory approval" is positive news — must not be caught by the negative list
        self.assertNotEqual(
            classify_news("CDSCO grants regulatory approval for new drug"),
            CatalystSentiment.NEGATIVE,
        )
```

- [ ] **Step 2: Run to confirm they fail**

```bash
PYTHONPATH=src python3 -m unittest tests.test_scanner.ProviderTests.test_classify_news_detects_new_negative_keywords tests.test_scanner.ProviderTests.test_classify_news_does_not_flag_generic_regulatory_as_negative -v
```

Expected: first test FAILs (keywords missing), second test may PASS (generic "regulatory" not yet in list) — that's fine; we just need at least one failure to confirm the test is meaningful.

- [ ] **Step 3: Fix `providers.py` — keywords, valuation arg, and remove dead parameter**

Replace lines 38-41 (`CATALYST_KEYWORDS`):

```python
CATALYST_KEYWORDS = {
    "positive": ("order", "contract", "deal", "beat", "guidance", "expansion", "approval", "upgrade"),
    "negative": (
        "pledge", "pledged", "fraud", "probe", "downgrade", "dilution", "sell-off",
        "insider selling", "block deal", "notice", "tax demand", "ED", "SEBI",
        "promoter sale", "regulatory violation", "regulatory action",
    ),
}
```

Replace the function `_estimate_valuation_percentile` (lines 266-270) — remove `forward_pe` parameter:

```python
def _estimate_valuation_percentile(trailing_pe: float) -> float:
    if trailing_pe <= 0:
        return 0.5
    return max(0.1, min(0.98, math.log1p(trailing_pe) / math.log1p(120.0)))
```

Update the call site (line 155):

```python
    valuation_percentile = _estimate_valuation_percentile(trailing_pe)
```

- [ ] **Step 4: Run tests**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/stock_scanner/providers.py tests/test_scanner.py
git commit -m "fix: remove duplicate valuation arg, expand negative sentiment keywords"
```

---

## Group B: Scoring Fixes

### Task 4: Fix Bug 4 — 52-week high proximity logic is inverted

**Files:**
- Modify: `src/stock_scanner/scoring.py` (lines 60-64)
- Modify: `tests/test_scanner.py` — fix `make_company` default, add new test

- [ ] **Step 1: Fix `make_company` default for `distance_from_52w_high_pct`**

In `tests/test_scanner.py` line 47, change:

```python
    distance_from_52w_high_pct: float = -4.0,
```

to:

```python
    distance_from_52w_high_pct: float = -0.04,
```

This aligns the test factory with the real provider output (decimal ratio, e.g. -0.04 = 4% below high).

- [ ] **Step 2: Write a failing test for the new 52w logic**

Add inside `ScoringTests`:

```python
    def test_near_52w_high_adds_setup_bonus(self) -> None:
        """Price within 10% of 52-week high should get the setup quality bonus."""
        near_high = make_company(
            "NEARHIGH",
            revenue=160.0, revenue_prev_year=120.0, revenue_prev_quarter=150.0,
            profit=38.0, profit_prev_year=28.0, profit_prev_quarter=34.0,
            distance_from_52w_high_pct=-0.05,  # 5% below high — within 10%
        )
        far_high = make_company(
            "FARHIGH",
            revenue=160.0, revenue_prev_year=120.0, revenue_prev_quarter=150.0,
            profit=38.0, profit_prev_year=28.0, profit_prev_quarter=34.0,
            distance_from_52w_high_pct=-0.35,  # 35% below high — deeply extended
        )
        near_result = score_company(near_high, as_of=date(2026, 4, 17))
        far_result = score_company(far_high, as_of=date(2026, 4, 17))

        self.assertGreater(near_result.setup_quality, far_result.setup_quality)
        self.assertIn("Price near 52-week high", near_result.positives)
        self.assertIn("Price far from 52-week high", far_result.risks)
```

- [ ] **Step 3: Run to confirm failure**

```bash
PYTHONPATH=src python3 -m unittest tests.test_scanner.ScoringTests.test_near_52w_high_adds_setup_bonus -v
```

Expected: FAIL — current logic gives far_high the bonus, not near_high.

- [ ] **Step 4: Fix `scoring.py` — invert the 52w high logic**

Replace lines 60-64:

```python
    if company.distance_from_52w_high_pct <= -0.02:
        setup_quality += 0.20
    else:
        setup_quality += 0.05
        risks.append("Price is close to the 52-week high")
```

with:

```python
    if company.distance_from_52w_high_pct >= -0.10:
        setup_quality += 0.20
        positives.append("Price near 52-week high")
    elif company.distance_from_52w_high_pct <= -0.30:
        setup_quality += 0.05
        risks.append("Price far from 52-week high")
    else:
        setup_quality += 0.12
```

- [ ] **Step 5: Run full suite**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: all tests pass (the default factory change to -0.04 keeps `test_high_growth_profitable_catalyst_stock_scores_high` at score ≥ 75 since -0.04 now earns the +0.20 bonus).

- [ ] **Step 6: Commit**

```bash
git add src/stock_scanner/scoring.py tests/test_scanner.py
git commit -m "fix: near 52-week high is now a setup bonus not a risk, fix test factory default"
```

---

### Task 5: Fix 5 + Fix 6 + Fix 7 — news recency decay, YoY ceiling, time_window_fit weight

**Files:**
- Modify: `src/stock_scanner/scoring.py`
- Test: `tests/test_scanner.py` — add new tests

- [ ] **Step 1: Write failing tests**

Add inside `ScoringTests`:

```python
    def test_old_news_contributes_less_to_catalyst_strength(self) -> None:
        """A fresh positive item should produce higher catalyst strength than a stale one."""
        fresh_news = make_company(
            "FRESH",
            revenue=160.0, revenue_prev_year=120.0, revenue_prev_quarter=150.0,
            profit=38.0, profit_prev_year=28.0, profit_prev_quarter=34.0,
            news=[make_news("Big contract win", CatalystSentiment.POSITIVE, days_ago=3)],
        )
        stale_news = make_company(
            "STALE",
            revenue=160.0, revenue_prev_year=120.0, revenue_prev_quarter=150.0,
            profit=38.0, profit_prev_year=28.0, profit_prev_quarter=34.0,
            news=[make_news("Big contract win", CatalystSentiment.POSITIVE, days_ago=60)],
        )
        fresh_result = score_company(fresh_news, as_of=date(2026, 4, 17))
        stale_result = score_company(stale_news, as_of=date(2026, 4, 17))

        self.assertGreater(fresh_result.catalyst_strength, stale_result.catalyst_strength)

    def test_25_pct_yoy_revenue_growth_yields_full_growth_score(self) -> None:
        """25% YoY growth should score 1.0 on the revenue growth input (ceiling = 0.25)."""
        company = make_company(
            "LARGECAP",
            revenue=125.0,
            revenue_prev_year=100.0,   # exactly 25% YoY
            revenue_prev_quarter=120.0,
            profit=30.0,
            profit_prev_year=24.0,     # 25% YoY
            profit_prev_quarter=28.0,
        )
        result = score_company(company, as_of=date(2026, 4, 17))
        # growth_score must be >= 0.80 when both YoY inputs are clamped to 1.0
        self.assertGreaterEqual(result.opportunity_score, 55)

    def test_time_window_fit_influences_opportunity_score(self) -> None:
        """Two companies with identical fundamentals but different catalyst recency should
        score differently because time_window_fit feeds into opportunity_raw."""
        base_kwargs = dict(
            revenue=160.0, revenue_prev_year=120.0, revenue_prev_quarter=150.0,
            profit=38.0, profit_prev_year=28.0, profit_prev_quarter=34.0,
        )
        high_twf = make_company(
            "HIGHTWF", **base_kwargs,
            news=[
                make_news("Order win", CatalystSentiment.POSITIVE, days_ago=2),
                make_news("Guidance raised", CatalystSentiment.POSITIVE, days_ago=5),
            ],
        )
        low_twf = make_company(
            "LOWTWF", **base_kwargs,
            news=[],
        )
        high_result = score_company(high_twf, as_of=date(2026, 4, 17))
        low_result = score_company(low_twf, as_of=date(2026, 4, 17))

        self.assertGreater(high_result.opportunity_score, low_result.opportunity_score)
        self.assertGreater(high_result.time_window_fit, low_result.time_window_fit)
```

- [ ] **Step 2: Run to confirm failures**

```bash
PYTHONPATH=src python3 -m unittest tests.test_scanner.ScoringTests.test_old_news_contributes_less_to_catalyst_strength tests.test_scanner.ScoringTests.test_25_pct_yoy_revenue_growth_yields_full_growth_score tests.test_scanner.ScoringTests.test_time_window_fit_influences_opportunity_score -v
```

Expected: `test_old_news_contributes_less` FAILs (no recency weighting yet). Others may pass with current logic — that's acceptable; they pin behaviour.

- [ ] **Step 3: Implement all three strategy fixes in `scoring.py`**

**Fix 5 — news recency decay.** After the imports at the top of `scoring.py`, add:

```python
def _news_weight(item, as_of: date) -> float:
    age = (as_of - item.published_at.date()).days
    if age <= 7:
        return 1.0
    if age <= 30:
        return 0.5
    return 0.1
```

Replace lines 45-47 (keep raw counts for labels/risk; add weighted scores only for `catalyst_strength`):

```python
    positive_news = sum(1 for item in company.news if item.sentiment is CatalystSentiment.POSITIVE)
    negative_news = sum(1 for item in company.news if item.sentiment is CatalystSentiment.NEGATIVE)
    positive_score = sum(_news_weight(i, as_of) for i in company.news if i.sentiment is CatalystSentiment.POSITIVE)
    negative_score = sum(_news_weight(i, as_of) for i in company.news if i.sentiment is CatalystSentiment.NEGATIVE)
    catalyst_strength = _clamp((positive_score * 0.28) - (negative_score * 0.18))
```

**Fix 6 — YoY growth ceiling.** In the `growth_inputs` list (lines 32-38), change the two YoY divisors from `0.50` to `0.25`:

```python
    growth_inputs = [
        _clamp(latest.revenue_yoy_growth / 0.25),
        _clamp(latest.profit_yoy_growth / 0.25),
        _clamp(latest.revenue_qoq_growth / 0.10),
        _clamp(latest.profit_qoq_growth / 0.10),
        _clamp(latest.margin_delta / 0.05),
    ]
```

**Fix 7 — wire `time_window_fit` into `opportunity_raw`.** Replace lines 88-94:

```python
    opportunity_raw = (
        (growth_score * 0.30)
        + (catalyst_strength * 0.25)
        + (setup_quality * 0.20)
        + (valuation_headroom * 0.15)
        + (risk_score * 0.10)
    )
```

with:

```python
    opportunity_raw = (
        (growth_score * 0.25)
        + (catalyst_strength * 0.20)
        + (setup_quality * 0.20)
        + (valuation_headroom * 0.15)
        + (risk_score * 0.10)
        + (time_window_fit * 0.10)
    )
```

- [ ] **Step 4: Run full suite**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/stock_scanner/scoring.py tests/test_scanner.py
git commit -m "feat: news recency decay, lower YoY ceiling to 25%, wire time_window_fit into score"
```

---

## Group C: Pipeline, Model, Reporting, and Frontend

### Task 6: Fix 9 + Fix 10 — hard-gate filter and late_entry_risk bucket

This task touches five files and needs to be done together because `ReportBundle` changes propagate everywhere.

**Files:**
- Modify: `src/stock_scanner/models.py`
- Modify: `src/stock_scanner/pipeline.py`
- Modify: `src/stock_scanner/reporting.py`
- Modify: `src/stock_scanner/frontend_data.py`
- Modify: `tests/test_scanner.py`

- [ ] **Step 1: Write failing tests**

Add inside `ReportingTests`:

```python
    def test_valuation_stretched_bucket_excludes_hard_gate_failures(self) -> None:
        """A company with stretched valuation but failing a hard gate must not appear
        in valuation_stretched — only investable companies belong there."""
        unprofitable_stretched = make_company(
            "BADVAL",
            revenue=200.0, revenue_prev_year=130.0, revenue_prev_quarter=175.0,
            profit=-5.0,   # unprofitable → hard gate fails
            profit_prev_year=10.0, profit_prev_quarter=8.0,
            valuation_percentile=0.95,
        )
        bundle = build_report_bundle([unprofitable_stretched], as_of=date(2026, 4, 17))
        tickers_in_stretched = [c.ticker for c in bundle.valuation_stretched]
        self.assertNotIn("BADVAL", tickers_in_stretched)

    def test_late_entry_risk_bucket_is_separate_from_avoid_for_now(self) -> None:
        """A company with Late-entry risk action label should appear in late_entry_risk,
        not in avoid_for_now."""
        stretched = make_company(
            "LATEENTRY",
            revenue=210.0, revenue_prev_year=130.0, revenue_prev_quarter=175.0,
            profit=54.0, profit_prev_year=30.0, profit_prev_quarter=42.0,
            last_price=145.0, sma_50=105.0, sma_200=88.0,
            distance_from_52w_high_pct=0.0,
            valuation_percentile=0.96,
            relative_strength_3m=0.34,
            news=[make_news("Q4 earnings beat", CatalystSentiment.POSITIVE)],
        )
        bundle = build_report_bundle([stretched], as_of=date(2026, 4, 17))

        self.assertIn("LATEENTRY", [c.ticker for c in bundle.late_entry_risk])
        self.assertNotIn("LATEENTRY", [c.ticker for c in bundle.avoid_for_now])

    def test_markdown_report_contains_late_entry_risk_section(self) -> None:
        stretched = make_company(
            "LATEENTRY",
            revenue=210.0, revenue_prev_year=130.0, revenue_prev_quarter=175.0,
            profit=54.0, profit_prev_year=30.0, profit_prev_quarter=42.0,
            last_price=145.0, sma_50=105.0, sma_200=88.0,
            distance_from_52w_high_pct=0.0,
            valuation_percentile=0.96,
            relative_strength_3m=0.34,
            news=[make_news("Q4 earnings beat", CatalystSentiment.POSITIVE)],
        )
        bundle = build_report_bundle([stretched], as_of=date(2026, 4, 17))
        report = render_markdown_report(bundle)
        self.assertIn("Late-entry risk", report)
        self.assertIn("LATEENTRY", report)
```

Also update the existing test that asserts STRETCH goes into `avoid_for_now`. In `test_report_bundle_groups_rankings_into_sections`, replace:

```python
        self.assertEqual(bundle.avoid_for_now[0].ticker, "STRETCH")
```

with:

```python
        self.assertEqual(bundle.late_entry_risk[0].ticker, "STRETCH")
```

- [ ] **Step 2: Run to confirm failures**

```bash
PYTHONPATH=src python3 -m unittest tests.test_scanner.ReportingTests -v
```

Expected: multiple FAILs — `late_entry_risk` attribute doesn't exist yet.

- [ ] **Step 3: Add `late_entry_risk` field to `ReportBundle` in `models.py`**

In `models.py`, change the `ReportBundle` dataclass (after `catalyst_watchlist` field):

```python
@dataclass(slots=True)
class ReportBundle:
    generated_for: date
    top_opportunities: list[ScoredCompany]
    catalyst_watchlist: list[ScoredCompany]
    late_entry_risk: list[ScoredCompany]
    valuation_stretched: list[ScoredCompany]
    high_growth_lacking_confirmation: list[ScoredCompany]
    avoid_for_now: list[ScoredCompany]
    important_developments: list[NewsItem]
```

Update `ReportBundle.to_dict()` to include the new field after `catalyst_watchlist`:

```python
    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_for": self.generated_for.isoformat(),
            "top_opportunities": [item.to_dict() for item in self.top_opportunities],
            "catalyst_watchlist": [item.to_dict() for item in self.catalyst_watchlist],
            "late_entry_risk": [item.to_dict() for item in self.late_entry_risk],
            "valuation_stretched": [item.to_dict() for item in self.valuation_stretched],
            "high_growth_lacking_confirmation": [
                item.to_dict() for item in self.high_growth_lacking_confirmation
            ],
            "avoid_for_now": [item.to_dict() for item in self.avoid_for_now],
            "important_developments": [item.to_dict() for item in self.important_developments],
        }
```

- [ ] **Step 4: Update `pipeline.py`**

In `build_report_bundle`, add the new bucket and fix the two existing ones:

```python
    late_entry_risk = [item for item in scored if item.action_label == "Late-entry risk"][:10]

    valuation_stretched = [
        item for item in scored
        if "Valuation looks stretched" in item.risks and item.passed_hard_gates
    ][:10]

    avoid_for_now = [item for item in scored if item.action_label == "Avoid for now"][:10]
```

Update the `ReportBundle(...)` constructor call to include `late_entry_risk=late_entry_risk` after `catalyst_watchlist`:

```python
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
```

- [ ] **Step 5: Update `reporting.py`**

In `render_markdown_report`, add the new section between `catalyst_watchlist` and `valuation_stretched`:

```python
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
```

- [ ] **Step 6: Update `frontend_data.py`**

In the `bucketCounts` dict inside `export_frontend_data`, add `lateEntryRisk` after `catalystWatchlist`:

```python
                "bucketCounts": {
                    "topOpportunities": len(payload["top_opportunities"]),
                    "catalystWatchlist": len(payload["catalyst_watchlist"]),
                    "lateEntryRisk": len(payload["late_entry_risk"]),
                    "valuationStretched": len(payload["valuation_stretched"]),
                    "highGrowthLackingConfirmation": len(
                        payload["high_growth_lacking_confirmation"]
                    ),
                    "avoidForNow": len(payload["avoid_for_now"]),
                },
```

- [ ] **Step 7: Run full suite**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/stock_scanner/models.py src/stock_scanner/pipeline.py src/stock_scanner/reporting.py src/stock_scanner/frontend_data.py tests/test_scanner.py
git commit -m "feat: add late_entry_risk bucket, exclude hard-gate failures from valuation_stretched"
```

---

## Task 7: Final verification

- [ ] **Step 1: Run full test suite**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: all tests green, zero failures.

- [ ] **Step 2: Syntax check**

```bash
PYTHONPATH=src python3 -m compileall src tests
```

Expected: no errors.

- [ ] **Step 3: Smoke test with demo mode**

```bash
PYTHONPATH=src python3 -m stock_scanner scan --demo --date 2026-04-17
```

Expected: scan completes, prints report summary with the new "Late-entry risk" section visible, no tracebacks.

- [ ] **Step 4: Commit if any fixups needed, otherwise done**
