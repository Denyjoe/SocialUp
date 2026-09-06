import { apiClient } from "../../client";
import type { AdminDashboardStats, RevenueTrendPoint } from "../../../types/admin";

export async function fetchDashboardStats(): Promise<AdminDashboardStats> {
  const { data } = await apiClient.get<AdminDashboardStats>("/admin/dashboard/stats/");
  return data;
}

export async function fetchRevenueTrend(days = 14): Promise<RevenueTrendPoint[]> {
  const { data } = await apiClient.get<RevenueTrendPoint[]>("/admin/dashboard/revenue-trend/", {
    params: { days },
  });
  return data;
}
