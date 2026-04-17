import type { ReportIndex, ReportPayload } from "../types";

const emptyIndex: ReportIndex = {
  latestReportDate: null,
  reports: [],
};

export async function loadReportIndex(): Promise<ReportIndex> {
  try {
    const response = await fetch(`${import.meta.env.BASE_URL}data/index.json`);
    if (!response.ok) {
      return emptyIndex;
    }
    return (await response.json()) as ReportIndex;
  } catch {
    return emptyIndex;
  }
}

export async function loadReportPayload(reportPath: string): Promise<ReportPayload> {
  const response = await fetch(`${import.meta.env.BASE_URL}data/${reportPath}`);
  if (!response.ok) {
    throw new Error(`Failed to load ${reportPath}`);
  }
  return (await response.json()) as ReportPayload;
}
