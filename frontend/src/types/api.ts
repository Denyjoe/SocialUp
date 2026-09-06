export interface UserProfile {
  id: number;
  email: string;
  phone_number: string;
  status: "active" | "suspended" | "banned";
  referral_code: string;
  is_staff: boolean;
  email_verified: boolean;
  phone_verified: boolean;
  date_joined: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: UserProfile;
}

export interface ApiError {
  detail?: string;
  [field: string]: unknown;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  platform: string;
  sort_order: number;
}

/** Cached 48h rollup backing the public Service Health dashboard. Null
 * fields mean too few recent orders to average meaningfully yet (see
 * MIN_SAMPLE_SIZE in the backend) — `sample_size` alone is still shown so
 * "not enough data" reads as a fact, not a broken page. */
export interface ServiceHealth {
  sample_size: number;
  avg_start_minutes: string | null;
  avg_speed_per_hour: string | null;
  refill_rate_percent: string | null;
  updated_at: string;
}

export interface Service {
  id: number;
  category: Category;
  name: string;
  description: string;
  service_type: string;
  min_quantity: number;
  max_quantity: number;
  retail_rate_per_1000: string;
  refill_enabled: boolean;
  cancel_enabled: boolean;
  average_time: string;
  health: ServiceHealth | null;
}

export type OrderStatus =
  | "pending"
  | "in_progress"
  | "processing"
  | "completed"
  | "partial"
  | "canceled"
  | "refunded"
  | "error";

export interface Order {
  id: string;
  service: number;
  service_name: string;
  link: string;
  quantity: number;
  charge_amount: string;
  discount_amount: string;
  status: OrderStatus;
  provider_order_id: string;
  start_count: number | null;
  remains: number | null;
  progress_percent: number | null;
  error_message: string;
  created_at: string;
}

export interface Wallet {
  currency: string;
  cached_balance: string;
  cached_balance_updated_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
