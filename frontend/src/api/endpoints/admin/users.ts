import { apiClient } from "../../client";
import type { AdminUser } from "../../../types/admin";
import type { Paginated } from "../../../types/api";

export interface AdminUserListParams {
  page?: number;
  search?: string;
  status?: string;
}

export async function fetchAdminUsers(params: AdminUserListParams): Promise<Paginated<AdminUser>> {
  const { data } = await apiClient.get<Paginated<AdminUser>>("/admin/users/", { params });
  return data;
}

export async function adjustUserBalance(
  userId: number,
  payload: { direction: "credit" | "debit"; amount: string; reason?: string }
): Promise<{ balance: string }> {
  const { data } = await apiClient.post(`/admin/users/${userId}/adjust-balance/`, payload);
  return data;
}

export async function setUserStatus(
  userId: number,
  newStatus: "active" | "suspended" | "banned"
): Promise<AdminUser> {
  const { data } = await apiClient.post<AdminUser>(`/admin/users/${userId}/status/`, {
    status: newStatus,
  });
  return data;
}
