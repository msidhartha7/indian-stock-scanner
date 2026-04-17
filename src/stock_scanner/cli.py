from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date
from pathlib import Path

from .demo_data import demo_companies
from .frontend_data import export_frontend_data
from .pipeline import build_report_bundle
from .providers import YahooFinanceClient
from .reporting import render_markdown_report
from .storage import ensure_storage, latest_report_date, load_bundle, save_report, save_snapshots
from .universe import load_universe, refresh_universe

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"
FRONTEND_DATA_ROOT = WEB_ROOT / "public" / "data"
PUBLISH_PATHS = ["data/reports", "web", ".codex", ".github"]


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

    publish = subparsers.add_parser(
        "publish", help="Run scan, refresh dashboard data, and push updates"
    )
    publish.add_argument("--date", dest="run_date", default=None, help="Publish date in YYYY-MM-DD")
    publish.add_argument(
        "--demo",
        action="store_true",
        help="Use bundled demo data instead of hitting public providers",
    )

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
        markdown_path, json_path = _run_scan(paths, as_of=as_of, use_demo=args.demo)
        print(f"Report written to {markdown_path}")
        print(f"JSON written to {json_path}")
        return 0

    if args.command == "publish":
        as_of = date.fromisoformat(args.run_date) if args.run_date else date.today()
        _run_scan(paths, as_of=as_of, use_demo=args.demo)
        _export_dashboard_data(paths)
        _run_frontend_build()
        if not _git_has_publish_changes():
            print("No publishable changes detected.")
            return 0
        _git_commit_publish(as_of.isoformat())
        _git_push_publish()
        print(f"Published stock dashboard for {as_of.isoformat()}")
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


def _run_scan(paths, *, as_of: date, use_demo: bool) -> tuple[Path, Path]:
    refresh_universe(paths)
    companies = demo_companies() if use_demo else _fetch_live_universe(paths)
    save_snapshots(paths, as_of, companies)
    bundle = build_report_bundle(companies, as_of=as_of)
    markdown = render_markdown_report(bundle)
    return save_report(paths, bundle, markdown)


def _export_dashboard_data(paths) -> None:
    export_frontend_data(paths, FRONTEND_DATA_ROOT)


def _run_frontend_build() -> None:
    _run_command(["npm", "run", "build"], cwd=WEB_ROOT)


def _git_has_publish_changes() -> bool:
    result = _run_command(["git", "status", "--short", "--", *PUBLISH_PATHS], cwd=PROJECT_ROOT)
    return bool(result.stdout.strip())


def _git_commit_publish(publish_date: str) -> None:
    _run_command(["git", "add", *PUBLISH_PATHS], cwd=PROJECT_ROOT)
    _run_command(["git", "commit", "-m", f"Publish stock scan for {publish_date}"], cwd=PROJECT_ROOT)


def _git_push_publish() -> None:
    _run_command(["git", "push"], cwd=PROJECT_ROOT)


def _run_command(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise SystemExit(f"{' '.join(command)} failed: {message}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
