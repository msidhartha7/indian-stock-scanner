# Usage Guide

## Setup

```bash
cd "/Users/sidhartha/Documents/New project/codex-hackatown/projects/indian-stock-scanner"
python3 -m venv venv
source venv/bin/activate
python3 --version
```

The scanner uses the standard library, and the dashboard adds a small Node-based frontend:

```bash
npm --prefix web install
```

## Running the Scanner

### 1. Refresh the starter universe

```bash
PYTHONPATH=src python3 -m stock_scanner refresh-universe
```

This rewrites `data/universe.json` with the bundled liquid NSE starter basket.

### 2. Run a demo scan

```bash
PYTHONPATH=src python3 -m stock_scanner scan --demo
```

Use this first to confirm the app is working end to end.

### 3. Run a dated demo scan

```bash
PYTHONPATH=src python3 -m stock_scanner scan --demo --date 2026-04-17
```

Useful when you want deterministic output during development or testing.

### 4. Run a live scan

```bash
PYTHONPATH=src python3 -m stock_scanner scan
```

This uses the public data adapters:

- Yahoo Finance for price and financial summary data
- Google News RSS for company/news catalyst discovery

If some tickers fail, the scan will still continue as long as at least one company succeeds.

## Viewing Results

### Show the latest report

```bash
PYTHONPATH=src python3 -m stock_scanner report --latest
```

### Explain a ticker from the latest report

```bash
PYTHONPATH=src python3 -m stock_scanner explain TRENT
```

This prints the exact stored JSON payload for that ticker, including:

- opportunity score
- action label
- growth metrics
- positives
- risks
- invalidation reason
- recent news

## Publishing The Dashboard

Run the one-command publish flow:

```bash
PYTHONPATH=src python3 -m stock_scanner publish
```

Use demo data when you want to verify the full publishing pipeline without live endpoints:

```bash
PYTHONPATH=src python3 -m stock_scanner publish --demo --date 2026-04-17
```

`publish` will:

- run the dated scan
- regenerate `web/public/data` from all checked-in reports
- build the Vite dashboard
- commit changed publish artifacts
- push to the tracked branch
- let GitHub Actions rebuild and deploy GitHub Pages automatically

## Report Output

Each scan writes:

- `data/reports/report-YYYY-MM-DD.md`
- `data/reports/report-YYYY-MM-DD.json`

The Markdown report includes:

- `Top 10 3-6 month opportunities`
- `Catalyst-driven watchlist`
- `Valuation-stretched names to avoid`
- `High-growth names lacking confirmation`
- `Avoid for now`
- `Important new developments since previous scan`

## Testing

Run the unit tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Run the dashboard production build:

```bash
npm --prefix web run build
```

Check import/bytecode compilation:

```bash
PYTHONPATH=src python3 -m compileall src tests
```

## Daily Workflow

```bash
source venv/bin/activate
cd "/Users/sidhartha/Documents/New project/codex-hackatown/projects/indian-stock-scanner"
PYTHONPATH=src python3 -m stock_scanner refresh-universe
PYTHONPATH=src python3 -m stock_scanner scan
PYTHONPATH=src python3 -m stock_scanner report --latest
PYTHONPATH=src python3 -m stock_scanner publish
```

Suggested habit:

1. Refresh the universe occasionally, not necessarily every day.
2. Run the scan once per day after market-relevant news is reasonably available.
3. Read the ranked report first.
4. Use `explain <ticker>` for deeper inspection before making any manual investment decision.

## Caveats

- Free public data can be incomplete or delayed.
- The bundled universe is a practical starter list, not full NSE 500 coverage.
- The scoring model is intentionally transparent but still heuristic.
- You should validate surfaced ideas manually before acting on them.
