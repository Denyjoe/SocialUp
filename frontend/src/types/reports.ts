export interface ReportSeriesPoint {
  date: string;
  revenue: string;
  cost: string;
  profit: string;
  orders: number;
}

export interface ReportSummary {
  range_days: number;
  revenue: string;
  cost: string;
  profit: string;
  margin_percent: string;
  discount_given: string;
  order_count: number;
  refunded_amount: string;
  refunded_count: number;
  deposits_total: string;
  series: ReportSeriesPoint[];
}

export interface ServiceMarginRow {
  service_id: number;
  service_name: string;
  category: string;
  orders: number;
  revenue: string;
  cost: string;
  profit: string;
  margin_percent: string;
}

export interface TopCustomerRow {
  user_id: number;
  email: string;
  orders: number;
  spent: string;
}

export interface PlatformProfitabilityRow {
  platform: string;
  orders: number;
  revenue: string;
  cost: string;
  profit: string;
  margin_percent: string;
}

export interface CategoryProfitabilityRow {
  category_id: number;
  category: string;
  platform: string;
  orders: number;
  revenue: string;
  profit: string;
  margin_percent: string;
}

export interface CategoryProfitabilityReport {
  platforms: PlatformProfitabilityRow[];
  categories: CategoryProfitabilityRow[];
}

export interface MarginBand {
  key: string;
  label: string;
  count: number;
}

export interface MarginDistributionRow {
  service_id: number;
  service_name: string;
  category: string;
  margin_percent: string;
}

export interface MarginDistributionReport {
  bands: MarginBand[];
  total_priced_services: number;
  worst: MarginDistributionRow[];
}
