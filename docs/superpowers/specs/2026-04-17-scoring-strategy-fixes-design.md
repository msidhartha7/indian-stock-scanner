# Scoring Strategy Fixes — Design Spec

**Date:** 2026-04-17
**Scope:** `providers.py`, `scoring.py`, `pipeline.py`, `models.py`, `reporting.py`, `frontend_data.py`

---

## Overview

Ten fixes to the stock evaluation strategy, split into two groups:
1. **Bugs** — four code defects with clear correct behaviour
2. **Strategy improvements** — six signal-quality and pipeline-logic upgrades

---

## Group 1: Bug Fixes

### Bug 1 — `valuation_percentile` duplicate argument (`providers.py:155`)

**Problem:** `_estimate_valuation_percentile(trailing_pe, trailing_pe)` passes the same value twice. The `forward_pe` parameter is never used meaningfully.

**Fix:**
- Remove `forward_pe` parameter from `_estimate_valuation_percentile`.
- Function body: use `trailing_pe` directly; return `0.5` if ≤ 0.
- Call site: `_estimate_valuation_percentile(trailing_pe)`.

---

### Bug 2 — `year_high` wrong fallback (`providers.py:150-152`)

**Problem:** `chartPreviousClose` (yesterday's close) is used as the fallback for the 52-week high when `fiftyTwoWeekHigh` is absent from Yahoo meta. This makes `distance_from_52w_high_pct` ≈ 0 for recently listed stocks.

**Fix:**
- Prefer `fiftyTwoWeekHigh` from meta when present.
- Fallback: `max(prices, default=current_price)` from the price series.

---

### Bug 3 — `updated_at` tracks price age, not earnings age (`providers.py:157`)

**Problem:** `updated_at` is set to the last price chart timestamp. The staleness hard gate (`age_days > MAX_STALE_DAYS`) therefore checks how recently the stock traded, not how old the financial data is. A company with 90-day-old earnings passes if it traded yesterday.

**Fix:**
- Set `updated_at = datetime.combine(latest_date, datetime.min.time(), tzinfo=timezone.utc)` where `latest_date` is the `as_of_date` of the most recent revenue entry.
- The price chart's last timestamp is still used for `_quarter_label` only.

---

### Bug 4 — 52-week high proximity logic inverted (`scoring.py:60-64`)

**Problem:** The current code gives a +0.20 setup bonus when the stock is NOT near its 52-week high, and flags near-high as a risk. For a momentum strategy, proximity to the 52-week high is constructive.

**Fix:** Three-tier logic replacing the binary check:

| Condition | Bonus | Label |
|-----------|-------|-------|
| `distance >= -0.10` (within 10% of high) | +0.20 | positive: "Price near 52-week high" |
| `-0.10 > distance > -0.30` | +0.12 | none |
| `distance <= -0.30` (deeply extended) | +0.05 | risk: "Price far from 52-week high" |

---

## Group 2: Strategy Improvements

### Fix 5 — News recency decay (`scoring.py`)

**Problem:** A 6-month-old article scores the same as yesterday's news in `catalyst_strength`.

**Fix:** Add `_news_weight(item: NewsItem, as_of: date) -> float`:
- Age ≤ 7 days → 1.0
- Age 8–30 days → 0.5
- Age > 30 days → 0.1

Replace raw `sum(1 for ...)` counts with weighted sums. `catalyst_strength` formula `_clamp((positive * 0.28) - (negative * 0.18))` is unchanged; only the weighted inputs change. The `as_of` date is already threaded into `score_company`.

---

### Fix 6 — Growth normalization ceiling (`scoring.py:32-35`)

**Problem:** 50% YoY ceiling heavily penalises large-caps that structurally cannot reach 50% growth. HDFC Bank at 15% YoY scores 0.30.

**Fix:** Lower YoY normalization from 0.50 → 0.25 for both revenue and profit YoY inputs. QoQ targets (0.10) and margin delta (0.05) unchanged.

```python
# Before
_clamp(latest.revenue_yoy_growth / 0.50),
_clamp(latest.profit_yoy_growth / 0.50),

# After
_clamp(latest.revenue_yoy_growth / 0.25),
_clamp(latest.profit_yoy_growth / 0.25),
```

---

### Fix 7 — Wire `time_window_fit` into `opportunity_score` (`scoring.py:87-95`)

**Problem:** `time_window_fit` is computed and stored but has no effect on ranking.

**Fix:** Add it to `opportunity_raw` with a 10% weight, reducing other weights proportionally:

| Dimension | Old weight | New weight |
|-----------|-----------|-----------|
| growth_score | 0.30 | 0.25 |
| catalyst_strength | 0.25 | 0.20 |
| setup_quality | 0.20 | 0.20 |
| valuation_headroom | 0.15 | 0.15 |
| risk_score | 0.10 | 0.10 |
| time_window_fit | — | 0.10 |

Action label thresholds (67 = "Research now", 55 = "Watch closely") remain unchanged.

---

### Fix 8 — Expand negative sentiment keywords (`providers.py:38-41`)

**Problem:** Key Indian equity red flags are missing; `"regulatory"` is too broad (regulatory approvals are positive).

**Fix:**
- Remove: `"regulatory"`
- Add to negative list: `"insider selling"`, `"block deal"`, `"notice"`, `"tax demand"`, `"ED"`, `"SEBI"`, `"promoter sale"`, `"regulatory violation"`, `"regulatory action"`

---

### Fix 9 — Exclude hard-gate failures from `valuation_stretched` bucket (`pipeline.py:21-23`)

**Problem:** Unprofitable or illiquid companies can appear in `valuation_stretched`, which implies they are otherwise investable.

**Fix:** Add `and item.passed_hard_gates` to the filter:

```python
valuation_stretched = [
    item for item in scored
    if "Valuation looks stretched" in item.risks and item.passed_hard_gates
][:10]
```

---

### Fix 10 — Separate `Late-entry risk` bucket (`pipeline.py`, `models.py`, downstream`)

**Problem:** `"Late-entry risk"` (high quality + stretched valuation = wait for pullback) is merged into `avoid_for_now`, losing the distinction.

**Fix:**
- Add `late_entry_risk: list[ScoredCompany]` field to `ReportBundle` (after `catalyst_watchlist`).
- Update `ReportBundle.to_dict()` to include `"late_entry_risk"`.
- `pipeline.py`: new filter `[item for item in scored if item.action_label == "Late-entry risk"][:10]`.
- Remove `"Late-entry risk"` from the `avoid_for_now` filter (keep only `"Avoid for now"`).
- `reporting.py`: add a new markdown section "Late-Entry Risk" between Catalyst Watchlist and Valuation Stretched.
- `frontend_data.py`: no change needed (copies full report JSON which already includes the new field).

---

## Files Changed

| File | Changes |
|------|---------|
| `providers.py` | Bug 1 (valuation arg), Bug 2 (year_high fallback), Bug 3 (updated_at), Fix 8 (keywords) |
| `scoring.py` | Bug 4 (52w logic), Fix 5 (recency decay), Fix 6 (YoY ceiling), Fix 7 (time_window_fit weight) |
| `pipeline.py` | Fix 9 (hard gate filter), Fix 10 (new bucket) |
| `models.py` | Fix 10 (new ReportBundle field) |
| `reporting.py` | Fix 10 (new markdown section) |

---

## Testing

- Existing unit tests run after each group to catch regressions.
- No new test files required: changes are deterministic transformations on existing data structures.
- Demo mode (`--demo`) exercises the full pipeline end-to-end after all changes.
