# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Indian Stock Opportunity Scanner — a local Python CLI tool for finding 3-6 month stock opportunities from NSE (National Stock Exchange of India). Combines earnings momentum, news catalysts, price setup, valuation, and risk scoring into dated Markdown/JSON reports. A React dashboard on GitHub Pages visualizes the reports.

## Commands

### Python (backend)

All commands: `PYTHONPATH=src python3 -m stock_scanner <command>`

```bash
PYTHONPATH=src python3 -m stock_scanner scan --demo          # safe test run with bundled data
PYTHONPATH=src python3 -m stock_scanner scan                 # live scan (Yahoo Finance + Google News)
PYTHONPATH=src python3 -m stock_scanner refresh-universe     # reset NSE ticker universe
PYTHONPATH=src python3 -m stock_scanner report --latest      # print latest report to stdout
PYTHONPATH=src python3 -m stock_scanner explain <TICKER>     # show full JSON for a ticker
PYTHONPATH=src python3 -m stock_scanner export-dashboard-data # rebuild static frontend data
PYTHONPATH=src python3 -m stock_scanner publish --demo       # scan → export → build → commit → push
```

### Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v      # run all tests
PYTHONPATH=src python3 -m compileall src tests               # check for syntax errors
```

### Frontend (web/)

```bash
npm --prefix web install
npm --prefix web run dev         # dev server
npm --prefix web run build       # production build + tsc type check
```

## Architecture

**Data flow:**
```
data/universe.json
  → providers.py (Yahoo Finance + Google News RSS)
  → models.py (CompanySnapshot)
  → scoring.py (ScoredCompany with 5 weighted dimensions)
  → pipeline.py (ReportBundle: 5 category buckets)
  → storage.py (data/reports/report-YYYY-MM-DD.{md,json})
  → frontend_data.py (web/public/data/reports/ + index.json)
  → React dashboard (web/src/App.tsx)
```

**Scoring dimensions** (hard gates filter first, then weighted score):
- Growth Score 30% — YoY/QoQ revenue & profit growth, margin expansion
- Catalyst Strength 25% — positive vs. negative news keyword weighting
- Setup Quality 20% — price > SMA50 > SMA200, momentum, distance from 52w high
- Valuation Headroom 15% — lower valuation percentile = more room
- Risk Score 10% — cash conversion, debt, news risk

Hard gates (reject if any fail): data freshness ≤14 days, profitable, revenue not collapsing (QoQ > -5%), liquid (avg daily value ≥ $1M).

**Action labels:** "Research now" (score ≥67) | "Watch closely" (≥55) | "Late-entry risk" | "Avoid for now"

**Report buckets:** Top Opportunities, Catalyst Watchlist, Valuation Stretched, High Growth Lacking Confirmation, Avoid For Now (top 10 each).

**Key design decisions:**
- No external Python dependencies — stdlib only (urllib, xml.etree, unittest)
- `--demo` mode uses bundled `demo_data.py` instead of live endpoints
- All models use `@dataclass(slots=True)`
- Reports are immutable dated artifacts; `publish` commits them and triggers GitHub Actions to rebuild the static site
- Dashboard is fully static — no runtime backend

**Key files:**
- `src/stock_scanner/cli.py` — entry point, command routing, git workflow for publish
- `src/stock_scanner/providers.py` — Yahoo Finance + Google News RSS fetching
- `src/stock_scanner/scoring.py` — all scoring weights/thresholds
- `src/stock_scanner/pipeline.py` — bucketing logic
- `src/stock_scanner/frontend_data.py` — generates `web/public/data/`
- `web/src/App.tsx` — React dashboard
