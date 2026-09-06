import { apiClient } from "../../client";
import type {
  CategoryProfitabilityReport,
  MarginDistributionReport,
  ReportSummary,
  ServiceMarginRow,
  TopCustomerRow,
} from "../../../types/reports";

export async function fetchReportSummary(days: number): Promise<ReportSummary> {
  const { data } = await apiClient.get<ReportSummary>("/admin/reports/summary/", {
    params: { days },
  });
  return data;
}

export async function fetchServiceMargins(days: number): Promise<ServiceMarginRow[]> {
  const { data } = await apiClient.get<{ results: ServiceMarginRow[] }>(
    "/admin/reports/service-margins/",
    { params: { days } }
  );
  return data.results;
}

export async function fetchTopCustomers(days: number): Promise<TopCustomerRow[]> {
  const { data } = await apiClient.get<{ results: TopCustomerRow[] }>(
    "/admin/reports/top-customers/",
    { params: { days } }
  );
  return data.results;
}

export async function fetchCategoryProfitability(days: number): Promise<CategoryProfitabilityReport> {
  const { data } = await apiClient.get<CategoryProfitabilityReport>(
    "/admin/reports/category-profitability/",
    { params: { days } }
  );
  return data;
}

/** Not date-ranged — a snapshot of the catalogue as it's priced right now,
 * independent of order history. */
export async function fetchMarginDistribution(): Promise<MarginDistributionReport> {
  const { data } = await apiClient.get<MarginDistributionReport>(
    "/admin/reports/margin-distribution/"
  );
  return data;
}

/** Downloads a CSV through axios so the request carries the auth header,
 * then hands the browser a blob. A plain link would hit the endpoint
 * unauthenticated and get a 403. */
export async function downloadCsv(kind: "orders" | "ledger", days: number): Promise<void> {
  const response = await apiClient.get(`/admin/exports/${kind}.csv`, {
    params: { days },
    responseType: "blob",
  });
  const url = URL.createObjectURL(new Blob([response.data], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `${kind}-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
