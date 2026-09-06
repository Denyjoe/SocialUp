import { apiClient } from "../client";
import type { AffiliateSummary, Referral } from "../../types/affiliate";
import type { Paginated } from "../../types/api";

export async function fetchAffiliateSummary(): Promise<AffiliateSummary> {
  const { data } = await apiClient.get<AffiliateSummary>("/affiliate/summary/");
  return data;
}

export async function fetchReferrals(): Promise<Referral[]> {
  const { data } = await apiClient.get<Paginated<Referral> | Referral[]>("/affiliate/referrals/", {
    params: { page_size: 100 },
  });
  return Array.isArray(data) ? data : data.results;
}
