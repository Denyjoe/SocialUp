import { apiClient } from "../../client";

export interface AdminAffiliateSettings {
  commission_percent: string;
  updated_at: string;
}

export async function fetchAdminAffiliateSettings(): Promise<AdminAffiliateSettings> {
  const { data } = await apiClient.get<AdminAffiliateSettings>("/admin/affiliate-settings/");
  return data;
}

export async function updateAdminAffiliateSettings(
  commission_percent: string
): Promise<AdminAffiliateSettings> {
  const { data } = await apiClient.patch<AdminAffiliateSettings>("/admin/affiliate-settings/", {
    commission_percent,
  });
  return data;
}
