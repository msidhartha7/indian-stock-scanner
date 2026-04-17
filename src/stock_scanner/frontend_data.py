from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from .storage import StoragePaths


@dataclass(slots=True)
class FrontendExportResult:
    latest_report_date: str | None
    report_dates: list[str]


def export_frontend_data(paths: StoragePaths, destination: Path) -> FrontendExportResult:
    destination.mkdir(parents=True, exist_ok=True)
    reports_dir = destination / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    for existing in reports_dir.glob("report-*.json"):
        existing.unlink()

    report_files = sorted(paths.reports_dir.glob("report-*.json"), reverse=True)
    reports: list[dict[str, object]] = []

    for report_file in report_files:
        payload = json.loads(report_file.read_text(encoding="utf-8"))
        report_name = report_file.name
        markdown_name = report_name.removesuffix(".json") + ".md"
        shutil.copyfile(report_file, reports_dir / report_name)
        markdown_source = paths.reports_dir / markdown_name
        if markdown_source.exists():
            shutil.copyfile(markdown_source, reports_dir / markdown_name)
        reports.append(
            {
                "date": payload["generated_for"],
                "reportPath": f"reports/{report_name}",
                "bucketCounts": {
                    "topOpportunities": len(payload["top_opportunities"]),
                    "catalystWatchlist": len(payload["catalyst_watchlist"]),
                    "valuationStretched": len(payload["valuation_stretched"]),
                    "highGrowthLackingConfirmation": len(
                        payload["high_growth_lacking_confirmation"]
                    ),
                    "avoidForNow": len(payload["avoid_for_now"]),
                },
                "topTickers": _top_tickers(payload),
            }
        )

    latest_report_date = reports[0]["date"] if reports else None
    index_payload = {
        "latestReportDate": latest_report_date,
        "reports": reports,
    }
    (destination / "index.json").write_text(json.dumps(index_payload, indent=2), encoding="utf-8")

    return FrontendExportResult(
        latest_report_date=latest_report_date,
        report_dates=[item["date"] for item in reports],
    )


def _top_tickers(report_payload: dict) -> list[str]:
    primary = report_payload["top_opportunities"] or report_payload["catalyst_watchlist"]
    return [item["ticker"] for item in primary[:3]]
