# Indian Stock Opportunity Scanner

Local Python CLI for finding `3-6 month` Indian stock opportunities from a liquid NSE universe using:

- earnings momentum
- near-term news catalysts
- price setup
- valuation sanity
- risk controls

The app generates a dated Markdown report and a JSON artifact for each scan, then can publish those results into a GitHub Pages dashboard from the same repository. It is built for manual daily use and is meant to help with research, not automate trading decisions.

## What It Does

- Maintains a starter liquid NSE universe
- Pulls public market and news data
- Scores stocks with hard gates plus a weighted ranking model
- Produces a daily ranked report
- Lets you inspect why a ticker was surfaced
- Ships a React dashboard with report history for GitHub Pages

## Project Structure

- `src/stock_scanner/`: CLI, providers, scoring, reporting, storage
- `web/`: Vite + React dashboard for GitHub Pages
- `tests/`: scoring and report behavior tests
- `data/universe.json`: current seed universe
- `data/cache/`: saved snapshot payloads
- `data/reports/`: generated Markdown and JSON reports
- `venv/`: local Python virtual environment

## Quick Start

```bash
cd "/Users/sidhartha/Documents/New project/codex-hackatown/projects/indian-stock-scanner"
python3 -m venv venv
source venv/bin/activate
PYTHONPATH=src python3 -m stock_scanner refresh-universe
PYTHONPATH=src python3 -m stock_scanner scan --demo
PYTHONPATH=src python3 -m stock_scanner report --latest
npm --prefix web install
PYTHONPATH=src python3 -m stock_scanner publish --demo
```

For day-to-day usage details, command examples, and output descriptions, see [USAGE.md](/Users/sidhartha/Documents/New%20project/codex-hackatown/projects/indian-stock-scanner/USAGE.md).

## Notes

- `scan --demo` is the safest first run because it verifies the full pipeline without depending on external endpoints.
- `scan` without `--demo` uses public Yahoo Finance endpoints plus Google News RSS.
- `publish` runs the dated scan, refreshes `web/public/data`, builds the dashboard, commits changed publish artifacts, pushes to the tracked branch, and lets GitHub Actions deploy GitHub Pages.
- `export-dashboard-data` rebuilds `web/public/data` from checked-in `data/reports` artifacts without running a new scan.
- GitHub Pages now runs `export-dashboard-data` during the deploy workflow, so the site can rebuild its report index directly from tracked report files.
- The provider layer is replaceable, so stronger data sources can be plugged in later without changing the CLI contract.
- This tool is a research assistant, not financial advice.
