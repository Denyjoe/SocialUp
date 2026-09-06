import { apiClient } from "../../client";
import type { AdminLedgerEntry } from "../../../types/admin";
import type { Paginated } from "../../../types/api";

export interface AdminLedgerListParams {
  page?: number;
  user?: string;
  entry_type?: string;
}

export async function fetchAdminLedger(
  params: AdminLedgerListParams
): Promise<Paginated<AdminLedgerEntry>> {
  const { data } = await apiClient.get<Paginated<AdminLedgerEntry>>("/admin/ledger/", { params });
  return data;
}
