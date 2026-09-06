export interface AdminUser {
  id: number;
  email: string;
  phone_number: string;
  status: "active" | "suspended" | "banned";
  is_staff: boolean;
  referral_code: string;
  date_joined: string;
  wallet_balance: string;
  wallet_currency: string;
  orders_count: number;
}

export interface AdminCategory {
  id: number;
  name: string;
  slug: string;
  platform: string;
  sort_order: number;
  is_active: boolean;
  services_count: number;
}

export interface AdminService {
  id: number;
  category: number;
  category_name: string;
  provider: number;
  provider_name: string;
  provider_service_id: string;
  name: string;
  description: string;
  service_type: string;
  min_quantity: number;
  max_quantity: number;
  cost_currency: string;
  cost_rate_per_1000: string;
  retail_rate_per_1000: string;
  margin_percent: number | null;
  markup_percent: string | null;
  price_locked: boolean;
  is_active: boolean;
  refill_enabled: boolean;
  cancel_enabled: boolean;
  average_time: string;
  last_synced_at: string | null;
}

export interface AdminPricingRule {
  id: number;
  name: string;
  scope: "category" | "platform" | "cost_tier";
  category: number | null;
  category_name: string | null;
  platform: string;
  min_cost_per_1000: string | null;
  max_cost_per_1000: string | null;
  markup_percent: string;
  min_profit_per_1000: string | null;
  priority: number;
  is_active: boolean;
  matching_services_count: number;
  created_at: string;
  updated_at: string;
}

export interface AdminProvider {
  id: number;
  name: string;
  provider_type: "mock" | "jap_style";
  base_url: string;
  has_api_key: boolean;
  is_active: boolean;
  balance_cached: string;
  balance_currency: string;
  balance_last_checked_at: string | null;
  services_count: number;
}

export interface AdminSyncLog {
  id: number;
  provider: number;
  provider_name: string;
  started_at: string;
  finished_at: string | null;
  services_created: number;
  services_updated: number;
  status: "success" | "failed";
  error_text: string;
}

export interface AdminOrder {
  id: string;
  user: number;
  user_email: string;
  service: number;
  service_name: string;
  provider: number;
  provider_name: string;
  link: string;
  quantity: number;
  charge_amount: string;
  cost_amount: string | null;
  cost_currency: string;
  status: string;
  provider_order_id: string;
  start_count: number | null;
  remains: number | null;
  progress_percent: number | null;
  error_message: string;
  refill_status: string | null;
  cancel_status: string | null;
  created_at: string;
  last_synced_at: string | null;
}

export interface AdminOrderStatusHistoryEntry {
  old_status: string;
  new_status: string;
  source: string;
  changed_at: string;
}

export interface AdminOrderDetail extends AdminOrder {
  status_history: AdminOrderStatusHistoryEntry[];
}

export interface AdminLedgerEntry {
  id: string;
  wallet: number;
  user_email: string;
  amount: string;
  balance_after: string;
  entry_type: string;
  reference_type: string;
  reference_id: string;
  description: string;
  created_by_email: string | null;
  created_at: string;
}

export interface AdminPlatformSettings {
  usd_to_local_rate: string;
  default_markup_percent: string;
  updated_at: string;
}

export interface PeriodStats {
  revenue: string;
  cost: string;
  profit: string;
  order_count: number;
}

export interface AdminDashboardStats {
  generated_at: string;
  users: { total: number; new_today: number; new_this_week: number };
  orders: { total: number; today: number; this_week: number; by_status: Record<string, number> };
  today: PeriodStats;
  this_week: PeriodStats;
  this_month: PeriodStats;
  all_time: PeriodStats;
  wallet_liability: string;
  providers: {
    id: number;
    name: string;
    is_active: boolean;
    balance_cached: string;
    balance_currency: string;
    balance_last_checked_at: string | null;
  }[];
  top_services_this_month: { service_id: number; name: string; order_count: number; revenue: string }[];
}

export interface RevenueTrendPoint {
  date: string;
  revenue: string;
  profit: string;
  orders: number;
}
