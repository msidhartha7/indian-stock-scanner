from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .demo_data import demo_companies
from .pipeline import build_report_bundle
from .providers import YahooFinanceClient
from .reporting import render_markdown_report
from .storage import ensure_storage, latest_report_date, load_bundle, save_report, save_snapshots
from .universe import load_universe, refresh_universe


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Indian stock opportunity scanner")
    parser.add_argument("--data-root", type=Path, default=None, help="Override data directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Run the daily scan")
    scan.add_argument("--date", dest="run_date", default=None, help="Scan date in YYYY-MM-DD")
    scan.add_argument(
        "--demo",
        action="store_true",
        help="Use bundled demo data instead of hitting public providers",
    )

    report = subparsers.add_parser("report", help="Print the latest report")
    report.add_argument("--latest", action="store_true", help="Show latest report")

    explain = subparsers.add_parser("explain", help="Explain a single ticker from latest report")
    explain.add_argument("ticker", help="Ticker to explain")

    subparsers.add_parser("refresh-universe", help="Reset the default liquid universe")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    paths = ensure_storage(args.data_root)

    if args.command == "refresh-universe":
        path = refresh_universe(paths)
        print(f"Universe refreshed at {path}")
        return 0

    if args.command == "scan":
        as_of = date.fromisoformat(args.run_date) if args.run_date else date.today()
        refresh_universe(paths)
        companies = demo_companies() if args.demo else _fetch_live_universe(paths)
        save_snapshots(paths, as_of, companies)
        bundle = build_report_bundle(companies, as_of=as_of)
        markdown = render_markdown_report(bundle)
        markdown_path, json_path = save_report(paths, bundle, markdown)
        print(f"Report written to {markdown_path}")
        print(f"JSON written to {json_path}")
        return 0

    if args.command == "report":
        report_date = latest_report_date(paths)
        if not report_date:
            raise SystemExit("No reports available yet. Run `scan` first.")
        print(paths.report_markdown_path(report_date).read_text(encoding="utf-8"))
        return 0

    if args.command == "explain":
        report_date = latest_report_date(paths)
        if not report_date:
            raise SystemExit("No reports available yet. Run `scan` first.")
        bundle = load_bundle(paths, report_date)
        ticker = args.ticker.upper()
        for section_name in (
            "top_opportunities",
            "catalyst_watchlist",
            "valuation_stretched",
            "high_growth_lacking_confirmation",
            "avoid_for_now",
        ):
            for company in bundle[section_name]:
                if company["ticker"] == ticker:
                    print(json.dumps(company, indent=2))
                    return 0
        raise SystemExit(f"{ticker} not found in latest report.")

    return 1


def _fetch_live_universe(paths) -> list:
    client = YahooFinanceClient()
    universe = load_universe(paths)
    companies = []
    errors: list[str] = []
    for item in universe:
        try:
            companies.append(client.fetch_company_snapshot(item))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{item['ticker']}: {exc}")
    if not companies:
        message = "No live data could be fetched."
        if errors:
            message += " " + "; ".join(errors[:5])
        raise SystemExit(message)
    if errors:
        print("Some tickers failed to fetch:")
        for error in errors[:10]:
            print(f"- {error}")
    return companies


if __name__ == "__main__":
    raise SystemExit(main())

