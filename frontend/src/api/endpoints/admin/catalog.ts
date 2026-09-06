import { apiClient } from "../../client";
import type {
  AdminCategory,
  AdminPlatformSettings,
  AdminPricingRule,
  AdminService,
} from "../../../types/admin";
import type { Paginated } from "../../../types/api";

export interface AdminServiceListParams {
  page?: number;
  search?: string;
  category?: number;
  provider?: number;
  is_active?: boolean;
}

export async function fetchAdminCategories(): Promise<AdminCategory[]> {
  const { data } = await apiClient.get<AdminCategory[]>("/admin/categories/");
  return data;
}

export async function fetchAdminServices(
  params: AdminServiceListParams
): Promise<Paginated<AdminService>> {
  const { data } = await apiClient.get<Paginated<AdminService>>("/admin/services/", { params });
  return data;
}

export async function updateAdminService(
  id: number,
  payload: Partial<
    Pick<AdminService, "retail_rate_per_1000" | "markup_percent" | "price_locked" | "is_active">
  >
): Promise<AdminService> {
  const { data } = await apiClient.patch<AdminService>(`/admin/services/${id}/`, payload);
  return data;
}

export interface BulkServiceUpdate {
  category?: number;
  provider?: number;
  action: string;
  value?: number;
}

export async function bulkUpdateServices(
  payload: BulkServiceUpdate
): Promise<{ detail: string; updated: number }> {
  const { data } = await apiClient.post("/admin/services/bulk-update/", payload);
  return data;
}

export async function fetchPlatformSettings(): Promise<AdminPlatformSettings> {
  const { data } = await apiClient.get<AdminPlatformSettings>("/admin/platform-settings/");
  return data;
}

export async function updatePlatformSettings(
  payload: Partial<Pick<AdminPlatformSettings, "usd_to_local_rate" | "default_markup_percent">>
): Promise<AdminPlatformSettings> {
  const { data } = await apiClient.patch<AdminPlatformSettings>("/admin/platform-settings/", payload);
  return data;
}

export async function fetchPricingRules(): Promise<AdminPricingRule[]> {
  const { data } = await apiClient.get<AdminPricingRule[]>("/admin/pricing-rules/");
  return data;
}

export type PricingRuleInput = Omit<
  AdminPricingRule,
  "id" | "category_name" | "matching_services_count" | "created_at" | "updated_at"
>;

export async function createPricingRule(payload: PricingRuleInput): Promise<AdminPricingRule> {
  const { data } = await apiClient.post<AdminPricingRule>("/admin/pricing-rules/", payload);
  return data;
}

export async function updatePricingRule(
  id: number,
  payload: Partial<PricingRuleInput>
): Promise<AdminPricingRule> {
  const { data } = await apiClient.patch<AdminPricingRule>(`/admin/pricing-rules/${id}/`, payload);
  return data;
}

export async function deletePricingRule(id: number): Promise<void> {
  await apiClient.delete(`/admin/pricing-rules/${id}/`);
}

export async function repriceFromRules(): Promise<{ detail: string; updated: number }> {
  const { data } = await apiClient.post("/admin/services/reprice-from-rules/");
  return data;
}
