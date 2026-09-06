import { apiClient } from "../../client";
import type { Paginated } from "../../../types/api";
import type { Coupon, CouponRedemption, DepositBonusRule } from "../../../types/promotions";

export interface CouponPayload {
  code: string;
  description?: string;
  discount_type: string;
  value: string;
  min_order_amount?: string;
  max_discount_amount?: string | null;
  max_uses?: number | null;
  max_uses_per_user?: number;
  expires_at?: string | null;
  is_active?: boolean;
}

export async function fetchCoupons(): Promise<Paginated<Coupon>> {
  const { data } = await apiClient.get<Paginated<Coupon>>("/admin/coupons/");
  return data;
}

export async function createCoupon(payload: CouponPayload): Promise<Coupon> {
  const { data } = await apiClient.post<Coupon>("/admin/coupons/", payload);
  return data;
}

export async function updateCoupon(id: number, payload: Partial<CouponPayload>): Promise<Coupon> {
  const { data } = await apiClient.patch<Coupon>(`/admin/coupons/${id}/`, payload);
  return data;
}

export async function deleteCoupon(id: number): Promise<void> {
  await apiClient.delete(`/admin/coupons/${id}/`);
}

export async function fetchCouponRedemptions(couponId?: number): Promise<Paginated<CouponRedemption>> {
  const { data } = await apiClient.get<Paginated<CouponRedemption>>("/admin/coupon-redemptions/", {
    params: couponId ? { coupon: couponId } : undefined,
  });
  return data;
}

export interface DepositBonusPayload {
  name: string;
  min_amount: string;
  bonus_percent: string;
  max_bonus_amount?: string | null;
  is_active?: boolean;
}

export async function fetchDepositBonuses(): Promise<Paginated<DepositBonusRule>> {
  const { data } = await apiClient.get<Paginated<DepositBonusRule>>("/admin/deposit-bonuses/");
  return data;
}

export async function createDepositBonus(payload: DepositBonusPayload): Promise<DepositBonusRule> {
  const { data } = await apiClient.post<DepositBonusRule>("/admin/deposit-bonuses/", payload);
  return data;
}

export async function updateDepositBonus(
  id: number,
  payload: Partial<DepositBonusPayload>
): Promise<DepositBonusRule> {
  const { data } = await apiClient.patch<DepositBonusRule>(`/admin/deposit-bonuses/${id}/`, payload);
  return data;
}

export async function deleteDepositBonus(id: number): Promise<void> {
  await apiClient.delete(`/admin/deposit-bonuses/${id}/`);
}
