import { apiClient } from "../../client";
import type { AdminProvider, AdminSyncLog } from "../../../types/admin";
import type { Paginated } from "../../../types/api";

export async function fetchAdminProviders(): Promise<AdminProvider[]> {
  const { data } = await apiClient.get<AdminProvider[]>("/admin/providers/");
  return data;
}

export async function updateAdminProvider(
  id: number,
  payload: Partial<Pick<AdminProvider, "name" | "base_url" | "is_active">> & { api_key?: string }
): Promise<AdminProvider> {
  const { data } = await apiClient.patch<AdminProvider>(`/admin/providers/${id}/`, payload);
  return data;
}

export async function createAdminProvider(payload: {
  name: string;
  provider_type: "mock" | "jap_style";
  base_url?: string;
  api_key?: string;
}): Promise<AdminProvider> {
  const { data } = await apiClient.post<AdminProvider>("/admin/providers/", payload);
  return data;
}

export async function triggerProviderSync(id: number): Promise<{ detail: string }> {
  const { data } = await apiClient.post(`/admin/providers/${id}/sync-services/`);
  return data;
}

export async function triggerProviderBalanceCheck(id: number): Promise<{ detail: string }> {
  const { data } = await apiClient.post(`/admin/providers/${id}/check-balance/`);
  return data;
}

export async function fetchProviderSyncLogs(providerId?: number): Promise<AdminSyncLog[]> {
  const { data } = await apiClient.get<Paginated<AdminSyncLog>>("/admin/providers/sync-logs/", {
    params: { page_size: 10, ...(providerId ? { provider: providerId } : {}) },
  });
  return data.results;
}
