export type DiscountType = "percent" | "fixed";

export interface Coupon {
  id: number;
  code: string;
  description: string;
  discount_type: DiscountType;
  value: string;
  min_order_amount: string;
  max_discount_amount: string | null;
  max_uses: number | null;
  max_uses_per_user: number;
  used_count: number;
  starts_at: string | null;
  expires_at: string | null;
  is_active: boolean;
  created_at: string;
}

export interface CouponRedemption {
  id: number;
  coupon_code: string;
  user_email: string;
  order: string | null;
  amount_discounted: string;
  created_at: string;
}

export interface DepositBonusRule {
  id: number;
  name: string;
  min_amount: string;
  bonus_percent: string;
  max_bonus_amount: string | null;
  is_active: boolean;
  starts_at: string | null;
  expires_at: string | null;
  created_at: string;
}
