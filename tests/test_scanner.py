from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from stock_scanner.models import (  # noqa: E402
    CatalystSentiment,
    CompanySnapshot,
    NewsItem,
    QuarterlyFinancials,
    ReportBundle,
)
from stock_scanner.pipeline import build_report_bundle  # noqa: E402
from stock_scanner.reporting import render_markdown_report  # noqa: E402
from stock_scanner.scoring import score_company  # noqa: E402


def make_company(
    ticker: str,
    *,
    revenue: float,
    revenue_prev_year: float,
    revenue_prev_quarter: float,
    profit: float,
    profit_prev_year: float,
    profit_prev_quarter: float,
    margin: float = 0.22,
    margin_prev_quarter: float = 0.18,
    operating_cash_flow: float = 120.0,
    total_debt: float = 20.0,
    last_price: float = 100.0,
    sma_50: float = 95.0,
    sma_200: float = 82.0,
    distance_from_52w_high_pct: float = -4.0,
    valuation_percentile: float = 0.55,
    relative_strength_3m: float = 0.18,
    avg_daily_value: float = 5_000_000.0,
    stale_days: int = 1,
    news: list[NewsItem] | None = None,
) -> CompanySnapshot:
    as_of = datetime(2026, 4, 17, tzinfo=timezone.utc) - timedelta(days=stale_days)
    return CompanySnapshot(
        ticker=ticker,
        company_name=f"{ticker} Limited",
        sector="Industrials",
        latest=QuarterlyFinancials(
            quarter="Q4FY26",
            revenue=revenue,
            revenue_prev_year=revenue_prev_year,
            revenue_prev_quarter=revenue_prev_quarter,
            net_profit=profit,
            profit_prev_year=profit_prev_year,
            profit_prev_quarter=profit_prev_quarter,
            operating_margin=margin,
            operating_margin_prev_quarter=margin_prev_quarter,
            operating_cash_flow=operating_cash_flow,
            total_debt=total_debt,
        ),
        trailing_twelve_month_profit=max(profit * 4, 1.0),
        last_price=last_price,
        sma_50=sma_50,
        sma_200=sma_200,
        distance_from_52w_high_pct=distance_from_52w_high_pct,
        valuation_percentile=valuation_percentile,
        relative_strength_3m=relative_strength_3m,
        avg_daily_value=avg_daily_value,
        updated_at=as_of,
        news=news or [],
    )


def make_news(title: str, sentiment: CatalystSentiment, *, days_ago: int = 2) -> NewsItem:
    published_at = datetime(2026, 4, 17, tzinfo=timezone.utc) - timedelta(days=days_ago)
    return NewsItem(
        source="Example News",
        title=title,
        url=f"https://example.com/{title.replace(' ', '-').lower()}",
        published_at=published_at,
        sentiment=sentiment,
    )


class ScoringTests(unittest.TestCase):
    def test_high_growth_profitable_catalyst_stock_scores_high(self) -> None:
        company = make_company(
            "ABC",
            revenue=180.0,
            revenue_prev_year=120.0,
            revenue_prev_quarter=160.0,
            profit=45.0,
            profit_prev_year=24.0,
            profit_prev_quarter=36.0,
            news=[
                make_news("Major order win boosts backlog", CatalystSentiment.POSITIVE),
                make_news("Management raises margin guidance", CatalystSentiment.POSITIVE),
            ],
        )

        result = score_company(company, as_of=date(2026, 4, 17))

        self.assertTrue(result.passed_hard_gates)
        self.assertGreaterEqual(result.opportunity_score, 75)
        self.assertEqual(result.action_label, "Research now")
        self.assertIn("Strong earnings momentum", result.positives)

    def test_overextended_stock_is_penalized(self) -> None:
        company = make_company(
            "EXT",
            revenue=210.0,
            revenue_prev_year=130.0,
            revenue_prev_quarter=175.0,
            profit=54.0,
            profit_prev_year=30.0,
            profit_prev_quarter=42.0,
            last_price=145.0,
            sma_50=105.0,
            sma_200=88.0,
            distance_from_52w_high_pct=0.0,
            valuation_percentile=0.96,
            relative_strength_3m=0.34,
            news=[make_news("Q4 earnings beat", CatalystSentiment.POSITIVE)],
        )

        result = score_company(company, as_of=date(2026, 4, 17))

        self.assertLess(result.opportunity_score, 75)
        self.assertIn("Valuation looks stretched", result.risks)
        self.assertIn("Late-entry risk", result.action_label)

    def test_good_fundamentals_without_catalyst_becomes_watchlist(self) -> None:
        company = make_company(
            "CALM",
            revenue=150.0,
            revenue_prev_year=104.0,
            revenue_prev_quarter=145.0,
            profit=31.0,
            profit_prev_year=20.0,
            profit_prev_quarter=29.0,
            news=[],
        )

        result = score_company(company, as_of=date(2026, 4, 17))

        self.assertTrue(result.passed_hard_gates)
        self.assertEqual(result.action_label, "Watch closely")
        self.assertLess(result.catalyst_strength, 0.35)

    def test_negative_governance_news_lowers_score(self) -> None:
        company = make_company(
            "RISK",
            revenue=170.0,
            revenue_prev_year=110.0,
            revenue_prev_quarter=156.0,
            profit=39.0,
            profit_prev_year=26.0,
            profit_prev_quarter=34.0,
            news=[
                make_news("Promoter stake pledged", CatalystSentiment.NEGATIVE),
                make_news("Quarterly revenue up sharply", CatalystSentiment.POSITIVE),
            ],
        )

        result = score_company(company, as_of=date(2026, 4, 17))

        self.assertIn("Governance or balance-sheet risk in recent news", result.risks)
        self.assertLess(result.risk_score, 0.6)

    def test_stale_company_data_fails_hard_gate(self) -> None:
        company = make_company(
            "OLD",
            revenue=160.0,
            revenue_prev_year=110.0,
            revenue_prev_quarter=150.0,
            profit=40.0,
            profit_prev_year=25.0,
            profit_prev_quarter=35.0,
            stale_days=25,
        )

        result = score_company(company, as_of=date(2026, 4, 17))

        self.assertFalse(result.passed_hard_gates)
        self.assertIn("Data is stale", result.rejection_reasons)


class ReportingTests(unittest.TestCase):
    def test_report_bundle_groups_rankings_into_sections(self) -> None:
        leaders = [
            make_company(
                "TOP1",
                revenue=180.0,
                revenue_prev_year=120.0,
                revenue_prev_quarter=162.0,
                profit=44.0,
                profit_prev_year=26.0,
                profit_prev_quarter=38.0,
                news=[make_news("Order win", CatalystSentiment.POSITIVE)],
            ),
            make_company(
                "TOP2",
                revenue=172.0,
                revenue_prev_year=116.0,
                revenue_prev_quarter=157.0,
                profit=41.0,
                profit_prev_year=28.0,
                profit_prev_quarter=37.0,
                news=[make_news("Guidance raised", CatalystSentiment.POSITIVE)],
            ),
        ]
        watch = make_company(
            "WATCH",
            revenue=150.0,
            revenue_prev_year=102.0,
            revenue_prev_quarter=142.0,
            profit=30.0,
            profit_prev_year=19.0,
            profit_prev_quarter=28.0,
        )
        stretched = make_company(
            "STRETCH",
            revenue=205.0,
            revenue_prev_year=128.0,
            revenue_prev_quarter=176.0,
            profit=48.0,
            profit_prev_year=32.0,
            profit_prev_quarter=39.0,
            valuation_percentile=0.97,
            last_price=152.0,
            sma_50=108.0,
            news=[make_news("Momentum continues", CatalystSentiment.POSITIVE)],
        )

        bundle = build_report_bundle(leaders + [watch, stretched], as_of=date(2026, 4, 17))

        self.assertIsInstance(bundle, ReportBundle)
        self.assertEqual(bundle.top_opportunities[0].ticker, "TOP1")
        self.assertEqual(bundle.catalyst_watchlist[0].ticker, "WATCH")
        self.assertEqual(bundle.avoid_for_now[0].ticker, "STRETCH")

    def test_markdown_report_contains_expected_sections(self) -> None:
        company = make_company(
            "TOP1",
            revenue=180.0,
            revenue_prev_year=120.0,
            revenue_prev_quarter=162.0,
            profit=44.0,
            profit_prev_year=26.0,
            profit_prev_quarter=38.0,
            news=[make_news("Order win", CatalystSentiment.POSITIVE)],
        )
        bundle = build_report_bundle([company], as_of=date(2026, 4, 17))

        report = render_markdown_report(bundle)

        self.assertIn("Top 10 3-6 month opportunities", report)
        self.assertIn("Catalyst-driven watchlist", report)
        self.assertIn("Important new developments since previous scan", report)
        self.assertIn("TOP1", report)

    def test_bundle_serializes_to_json(self) -> None:
        company = make_company(
            "TOP1",
            revenue=180.0,
            revenue_prev_year=120.0,
            revenue_prev_quarter=162.0,
            profit=44.0,
            profit_prev_year=26.0,
            profit_prev_quarter=38.0,
            news=[make_news("Order win", CatalystSentiment.POSITIVE)],
        )
        bundle = build_report_bundle([company], as_of=date(2026, 4, 17))

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "bundle.json"
            output_path.write_text(json.dumps(bundle.to_dict(), indent=2), encoding="utf-8")
            restored = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(restored["generated_for"], "2026-04-17")
        self.assertEqual(restored["top_opportunities"][0]["ticker"], "TOP1")


class FrontendExportTests(unittest.TestCase):
    def test_export_frontend_data_writes_index_and_report_files(self) -> None:
        from stock_scanner.frontend_data import export_frontend_data
        from stock_scanner.storage import ensure_storage, save_report

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = ensure_storage(root / "data")
            public_dir = root / "web" / "public" / "data"

            older_bundle = build_report_bundle(
                [
                    make_company(
                        "OLD1",
                        revenue=180.0,
                        revenue_prev_year=120.0,
                        revenue_prev_quarter=160.0,
                        profit=45.0,
                        profit_prev_year=24.0,
                        profit_prev_quarter=36.0,
                        news=[make_news("Older catalyst", CatalystSentiment.POSITIVE, days_ago=4)],
                    )
                ],
                as_of=date(2026, 4, 16),
            )
            latest_bundle = build_report_bundle(
                [
                    make_company(
                        "NEW1",
                        revenue=200.0,
                        revenue_prev_year=125.0,
                        revenue_prev_quarter=170.0,
                        profit=52.0,
                        profit_prev_year=30.0,
                        profit_prev_quarter=40.0,
                        news=[make_news("Fresh catalyst", CatalystSentiment.POSITIVE, days_ago=1)],
                    )
                ],
                as_of=date(2026, 4, 17),
            )

            save_report(paths, older_bundle, render_markdown_report(older_bundle))
            save_report(paths, latest_bundle, render_markdown_report(latest_bundle))

            result = export_frontend_data(paths, public_dir)

            self.assertEqual(result.latest_report_date, "2026-04-17")
            self.assertEqual(result.report_dates, ["2026-04-17", "2026-04-16"])
            index_payload = json.loads((public_dir / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(index_payload["latestReportDate"], "2026-04-17")
            self.assertEqual(index_payload["reports"][0]["date"], "2026-04-17")
            self.assertEqual(index_payload["reports"][0]["reportPath"], "reports/report-2026-04-17.json")
            self.assertTrue((public_dir / "reports" / "report-2026-04-17.json").exists())
            self.assertTrue((public_dir / "reports" / "report-2026-04-17.md").exists())
            latest_payload = json.loads(
                (public_dir / "reports" / "report-2026-04-17.json").read_text(encoding="utf-8")
            )
            self.assertEqual(latest_payload["generated_for"], "2026-04-17")

    def test_export_frontend_data_promotes_watchlist_when_top_opportunities_is_empty(self) -> None:
        from stock_scanner.frontend_data import export_frontend_data
        from stock_scanner.storage import ensure_storage, save_report

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = ensure_storage(root / "data")
            public_dir = root / "web" / "public" / "data"

            watch_bundle = build_report_bundle(
                [
                    make_company(
                        "WATCH1",
                        revenue=150.0,
                        revenue_prev_year=104.0,
                        revenue_prev_quarter=145.0,
                        profit=31.0,
                        profit_prev_year=20.0,
                        profit_prev_quarter=29.0,
                        news=[],
                    )
                ],
                as_of=date(2026, 4, 17),
            )

            save_report(paths, watch_bundle, render_markdown_report(watch_bundle))

            export_frontend_data(paths, public_dir)

            index_payload = json.loads((public_dir / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(index_payload["reports"][0]["topTickers"], ["WATCH1"])
            self.assertEqual(index_payload["reports"][0]["bucketCounts"]["topOpportunities"], 0)
            self.assertEqual(index_payload["reports"][0]["bucketCounts"]["catalystWatchlist"], 1)


class PublishCommandTests(unittest.TestCase):
    def test_publish_command_runs_scan_export_build_and_git_steps(self) -> None:
        from stock_scanner import cli

        with patch.object(cli, "_run_scan") as run_scan, patch.object(
            cli, "_export_dashboard_data"
        ) as export_data, patch.object(cli, "_run_frontend_build") as build_app, patch.object(
            cli, "_git_has_publish_changes", return_value=True
        ) as has_changes, patch.object(cli, "_git_commit_publish") as git_commit, patch.object(
            cli, "_git_push_publish"
        ) as git_push:
            result = cli.main(["--data-root", "/tmp/data", "publish", "--date", "2026-04-17"])

        self.assertEqual(result, 0)
        run_scan.assert_called_once()
        export_data.assert_called_once()
        build_app.assert_called_once()
        has_changes.assert_called_once()
        git_commit.assert_called_once_with("2026-04-17")
        git_push.assert_called_once()

    def test_publish_command_skips_commit_and_push_when_no_changes(self) -> None:
        from stock_scanner import cli

        with patch.object(cli, "_run_scan"), patch.object(cli, "_export_dashboard_data"), patch.object(
            cli, "_run_frontend_build"
        ), patch.object(cli, "_git_has_publish_changes", return_value=False), patch.object(
            cli, "_git_commit_publish"
        ) as git_commit, patch.object(cli, "_git_push_publish") as git_push:
            result = cli.main(["--data-root", "/tmp/data", "publish", "--date", "2026-04-17"])

        self.assertEqual(result, 0)
        git_commit.assert_not_called()
        git_push.assert_not_called()

    def test_publish_command_reports_success_when_no_changes_exist(self) -> None:
        from stock_scanner import cli

        with patch.object(cli, "_run_scan"), patch.object(cli, "_export_dashboard_data"), patch.object(
            cli, "_run_frontend_build"
        ), patch.object(cli, "_git_has_publish_changes", return_value=False), patch(
            "builtins.print"
        ) as print_mock:
            result = cli.main(["publish", "--date", "2026-04-17", "--demo"])

        self.assertEqual(result, 0)
        print_mock.assert_any_call("No publishable changes detected.")

    def test_git_has_publish_changes_only_detects_owned_paths(self) -> None:
        from stock_scanner import cli

        with patch.object(
            cli,
            "_run_command",
            return_value=subprocess.CompletedProcess(
                args=["git"],
                returncode=0,
                stdout=" M data/reports/report-2026-04-17.json\n",
                stderr="",
            ),
        ) as run_command:
            self.assertTrue(cli._git_has_publish_changes())

        run_command.assert_called_once_with(
            ["git", "status", "--short", "--", "data/reports", "web", ".codex", ".github"],
            cwd=cli.PROJECT_ROOT,
        )

    def test_git_has_publish_changes_returns_false_for_clean_status(self) -> None:
        from stock_scanner import cli

        with patch.object(
            cli,
            "_run_command",
            return_value=subprocess.CompletedProcess(
                args=["git"],
                returncode=0,
                stdout="",
                stderr="",
            ),
        ):
            self.assertFalse(cli._git_has_publish_changes())


if __name__ == "__main__":
    unittest.main()
