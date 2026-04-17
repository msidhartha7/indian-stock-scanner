import { useEffect, useState } from "react";
import { loadReportIndex, loadReportPayload } from "./lib/loadReports";
import type { Recommendation, ReportIndex, ReportPayload } from "./types";

const sections = [
  ["top_opportunities", "Top Opportunities"],
  ["catalyst_watchlist", "Catalyst Watchlist"],
  ["valuation_stretched", "Valuation Stretched"],
  ["high_growth_lacking_confirmation", "High Growth Lacking Confirmation"],
  ["avoid_for_now", "Avoid For Now"],
] as const;

type SectionKey = (typeof sections)[number][0];
const repositoryBase = import.meta.env.BASE_URL;

function App() {
  const [index, setIndex] = useState<ReportIndex | null>(null);
  const [activeDate, setActiveDate] = useState("");
  const [report, setReport] = useState<ReportPayload | null>(null);
  const [selected, setSelected] = useState<Recommendation | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    loadReportIndex()
      .then((payload) => {
        setIndex(payload);
        if (payload.latestReportDate) {
          setActiveDate(payload.latestReportDate);
        }
      })
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "Failed to load report index.");
      });
  }, []);

  useEffect(() => {
    if (!activeDate || !index) {
      return;
    }

    const entry = index.reports.find((item) => item.date === activeDate);
    if (!entry) {
      setReport(null);
      setSelected(null);
      return;
    }

    loadReportPayload(entry.reportPath)
      .then((payload) => {
        setReport(payload);
        setSelected(payload.top_opportunities[0] ?? payload.catalyst_watchlist[0] ?? null);
      })
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "Failed to load report payload.");
      });
  }, [activeDate, index]);

  const filteredRecommendations = getFilteredRecommendations(report, query);
  const activeEntry = index?.reports.find((item) => item.date === activeDate) ?? null;

  return (
    <div className="app-shell">
      <aside className="history-panel">
        <p className="eyebrow">Indian Stock Scanner</p>
        <h1>Recommendation Dashboard</h1>
        <p className="muted">
          Latest recommendations, watchlists, and historical scans from the dated report archive.
        </p>
        <div className="history-list">
          {index?.reports.map((entry) => (
            <button
              key={entry.date}
              type="button"
              className={entry.date === activeDate ? "history-item active" : "history-item"}
              onClick={() => setActiveDate(entry.date)}
            >
              <span>{entry.date}</span>
              <strong>{entry.topTickers.join(", ") || "No promoted names"}</strong>
            </button>
          ))}
        </div>
      </aside>

      <main className="dashboard">
        <section className="hero">
          <div>
            <p className="eyebrow">Active Report</p>
            <h2>{activeDate || "No reports loaded"}</h2>
            <p className="muted">
              {report?.top_opportunities.length
                ? "Top-tier names qualified for immediate research."
                : "No names qualified for the top tier. Watchlist leaders are promoted instead."}
            </p>
          </div>
          <label className="search-field">
            <span>Filter recommendations</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ticker, sector, or action"
            />
          </label>
        </section>

        {error ? <p className="error-banner">{error}</p> : null}

        <section className="summary-grid">
          <SummaryCard label="Top Opportunities" value={activeEntry?.bucketCounts.topOpportunities ?? 0} />
          <SummaryCard label="Catalyst Watchlist" value={activeEntry?.bucketCounts.catalystWatchlist ?? 0} />
          <SummaryCard label="Valuation Stretched" value={activeEntry?.bucketCounts.valuationStretched ?? 0} />
          <SummaryCard label="Avoid For Now" value={activeEntry?.bucketCounts.avoidForNow ?? 0} />
        </section>

        <section className="content-grid">
          <div className="recommendation-table">
            <div className="table-header">
              <span>Ticker</span>
              <span>Action</span>
              <span>Score</span>
              <span>Sector</span>
            </div>
            {filteredRecommendations.map((item) => (
              <button
                key={item.ticker}
                type="button"
                className={selected?.ticker === item.ticker ? "table-row selected" : "table-row"}
                onClick={() => setSelected(item)}
              >
                <strong>{item.ticker}</strong>
                <span>{item.action_label}</span>
                <span>{item.opportunity_score}</span>
                <span>{item.sector}</span>
              </button>
            ))}
          </div>

          <article className="detail-panel">
            {selected ? (
              <>
                <p className="eyebrow">{selected.action_label}</p>
                <h3>
                  {selected.ticker} <span>{selected.company_name}</span>
                </h3>
                <p className="muted">{selected.summary}</p>
                <div className="metric-grid">
                  <Metric label="Setup" value={toPercent(selected.setup_quality)} />
                  <Metric label="Catalyst" value={toPercent(selected.catalyst_strength)} />
                  <Metric label="Valuation" value={toPercent(selected.valuation_stretch)} />
                  <Metric label="Risk" value={toPercent(selected.risk_score)} />
                </div>
                <p>
                  <strong>Positives:</strong> {selected.positives.join(", ") || "None"}
                </p>
                <p>
                  <strong>Risks:</strong> {selected.risks.join(", ") || "None"}
                </p>
                <p>
                  <strong>Invalidation:</strong> {selected.invalidation_reason}
                </p>
                <div className="financials">
                  <div>
                    <span>Quarter</span>
                    <strong>{selected.latest.quarter}</strong>
                  </div>
                  <div>
                    <span>Revenue</span>
                    <strong>{formatCurrency(selected.latest.revenue)}</strong>
                  </div>
                  <div>
                    <span>Net Profit</span>
                    <strong>{formatCurrency(selected.latest.net_profit)}</strong>
                  </div>
                  <div>
                    <span>Price</span>
                    <strong>{selected.last_price.toFixed(2)}</strong>
                  </div>
                </div>
                <ul className="news-list">
                  {selected.news.slice(0, 5).map((item) => (
                    <li key={item.url}>
                      <a href={item.url} target="_blank" rel="noreferrer">
                        {item.title}
                      </a>
                    </li>
                  ))}
                </ul>
                {activeDate ? (
                  <p className="artifact-links">
                    <a href={artifactPath(activeDate, "json")} target="_blank" rel="noreferrer">
                      JSON
                    </a>
                    <a href={artifactPath(activeDate, "md")} target="_blank" rel="noreferrer">
                      Markdown
                    </a>
                  </p>
                ) : null}
              </>
            ) : (
              <p className="muted">Choose a stock to inspect the thesis, risks, and recent news.</p>
            )}
          </article>
        </section>

        <section className="bucket-sections">
          {report
            ? sections.map(([key, label]) => (
                <article key={key} className="bucket-panel">
                  <div className="bucket-header">
                    <h3>{label}</h3>
                    <span>{report[key].length}</span>
                  </div>
                  {report[key].length ? (
                    report[key].map((item) => (
                      <button
                        key={`${key}-${item.ticker}`}
                        type="button"
                        className="bucket-item"
                        onClick={() => setSelected(item)}
                      >
                        <strong>{item.ticker}</strong>
                        <span>{item.action_label}</span>
                      </button>
                    ))
                  ) : (
                    <p className="muted">No names in this bucket for the active report.</p>
                  )}
                </article>
              ))
            : null}
        </section>
      </main>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <article className="summary-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function getFilteredRecommendations(report: ReportPayload | null, query: string): Recommendation[] {
  if (!report) {
    return [];
  }

  const all = sections.flatMap(([key]) => report[key]);
  const deduped = Array.from(new Map(all.map((item) => [item.ticker, item])).values());
  const needle = query.trim().toLowerCase();

  if (!needle) {
    return deduped;
  }

  return deduped.filter((item) => {
    return (
      item.ticker.toLowerCase().includes(needle) ||
      item.company_name.toLowerCase().includes(needle) ||
      item.sector.toLowerCase().includes(needle) ||
      item.action_label.toLowerCase().includes(needle)
    );
  });
}

function toPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: 0,
  }).format(value);
}

function artifactPath(dateValue: string, extension: "json" | "md"): string {
  return `${repositoryBase}data/reports/report-${dateValue}.${extension}`;
}

export default App;
