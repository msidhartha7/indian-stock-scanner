from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .models import CatalystSentiment, CompanySnapshot, NewsItem, QuarterlyFinancials, ReportBundle


DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[2] / "data"


@dataclass(slots=True)
class StoragePaths:
    root: Path

    @property
    def cache_dir(self) -> Path:
        return self.root / "cache"

    @property
    def reports_dir(self) -> Path:
        return self.root / "reports"

    @property
    def universe_path(self) -> Path:
        return self.root / "universe.json"

    def snapshots_path(self, as_of: date) -> Path:
        return self.cache_dir / f"snapshots-{as_of.isoformat()}.json"

    def report_markdown_path(self, as_of: date) -> Path:
        return self.reports_dir / f"report-{as_of.isoformat()}.md"

    def report_json_path(self, as_of: date) -> Path:
        return self.reports_dir / f"report-{as_of.isoformat()}.json"


def ensure_storage(root: Path | None = None) -> StoragePaths:
    paths = StoragePaths(root=root or DEFAULT_DATA_ROOT)
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.cache_dir.mkdir(parents=True, exist_ok=True)
    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    return paths


def save_snapshots(paths: StoragePaths, as_of: date, companies: list[CompanySnapshot]) -> Path:
    payload = [company.to_dict() for company in companies]
    output_path = paths.snapshots_path(as_of)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def load_snapshots(paths: StoragePaths, as_of: date) -> list[CompanySnapshot]:
    raw_items = json.loads(paths.snapshots_path(as_of).read_text(encoding="utf-8"))
    return [_snapshot_from_dict(item) for item in raw_items]


def save_report(paths: StoragePaths, bundle: ReportBundle, markdown: str) -> tuple[Path, Path]:
    markdown_path = paths.report_markdown_path(bundle.generated_for)
    json_path = paths.report_json_path(bundle.generated_for)
    markdown_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(bundle.to_dict(), indent=2), encoding="utf-8")
    return markdown_path, json_path


def load_bundle(paths: StoragePaths, as_of: date) -> dict:
    return json.loads(paths.report_json_path(as_of).read_text(encoding="utf-8"))


def latest_report_date(paths: StoragePaths) -> date | None:
    report_files = sorted(paths.reports_dir.glob("report-*.json"))
    if not report_files:
        return None
    latest = report_files[-1].stem.removeprefix("report-")
    return date.fromisoformat(latest)


def _snapshot_from_dict(raw: dict) -> CompanySnapshot:
    return CompanySnapshot(
        ticker=raw["ticker"],
        company_name=raw["company_name"],
        sector=raw["sector"],
        latest=QuarterlyFinancials(**raw["latest"]),
        trailing_twelve_month_profit=raw["trailing_twelve_month_profit"],
        last_price=raw["last_price"],
        sma_50=raw["sma_50"],
        sma_200=raw["sma_200"],
        distance_from_52w_high_pct=raw["distance_from_52w_high_pct"],
        valuation_percentile=raw["valuation_percentile"],
        relative_strength_3m=raw["relative_strength_3m"],
        avg_daily_value=raw["avg_daily_value"],
        updated_at=datetime.fromisoformat(raw["updated_at"]),
        news=[
            NewsItem(
                source=item["source"],
                title=item["title"],
                url=item["url"],
                published_at=datetime.fromisoformat(item["published_at"]),
                sentiment=CatalystSentiment(item["sentiment"]),
            )
            for item in raw["news"]
        ],
    )

