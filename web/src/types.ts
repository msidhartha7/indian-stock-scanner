export type NewsItem = {
  source: string;
  title: string;
  url: string;
  published_at: string;
  sentiment: string;
};

export type Recommendation = {
  ticker: string;
  company_name: string;
  sector: string;
  opportunity_score: number;
  action_label: string;
  time_window_fit: number;
  catalyst_strength: number;
  valuation_stretch: number;
  setup_quality: number;
  risk_score: number;
  positives: string[];
  risks: string[];
  summary: string;
  invalidation_reason: string;
  last_price: number;
  updated_at: string;
  news: NewsItem[];
  latest: {
    quarter: string;
    revenue: number;
    revenue_prev_year: number;
    revenue_prev_quarter: number;
    net_profit: number;
    profit_prev_year: number;
    profit_prev_quarter: number;
    operating_margin: number;
    operating_margin_prev_quarter: number;
    operating_cash_flow: number;
    total_debt: number;
  };
};

export type ReportPayload = {
  generated_for: string;
  top_opportunities: Recommendation[];
  catalyst_watchlist: Recommendation[];
  valuation_stretched: Recommendation[];
  high_growth_lacking_confirmation: Recommendation[];
  avoid_for_now: Recommendation[];
};

export type ReportIndexEntry = {
  date: string;
  reportPath: string;
  topTickers: string[];
  bucketCounts: {
    topOpportunities: number;
    catalystWatchlist: number;
    valuationStretched: number;
    highGrowthLackingConfirmation: number;
    avoidForNow: number;
  };
};

export type ReportIndex = {
  latestReportDate: string | null;
  reports: ReportIndexEntry[];
};
