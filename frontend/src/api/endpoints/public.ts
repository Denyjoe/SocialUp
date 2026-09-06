import { apiClient } from "../client";

export interface PublicStats {
  users: number;
  services: number;
  orders_completed: number;
}

export async function fetchPublicStats(): Promise<PublicStats> {
  const { data } = await apiClient.get<PublicStats>("/public/stats/");
  return data;
}
