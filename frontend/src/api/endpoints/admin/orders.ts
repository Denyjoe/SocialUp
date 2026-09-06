import { apiClient } from "../../client";
import type { AdminOrder, AdminOrderDetail } from "../../../types/admin";
import type { Paginated } from "../../../types/api";

export interface AdminOrderListParams {
  page?: number;
  status?: string;
  user?: string;
  date_from?: string;
  date_to?: string;
}

export async function fetchAdminOrders(params: AdminOrderListParams): Promise<Paginated<AdminOrder>> {
  const { data } = await apiClient.get<Paginated<AdminOrder>>("/admin/orders/", { params });
  return data;
}

export async function fetchAdminOrderDetail(id: string): Promise<AdminOrderDetail> {
  const { data } = await apiClient.get<AdminOrderDetail>(`/admin/orders/${id}/`);
  return data;
}

export async function refundAdminOrder(id: string, reason?: string): Promise<AdminOrder> {
  const { data } = await apiClient.post<AdminOrder>(`/admin/orders/${id}/refund/`, { reason });
  return data;
}

export async function retrySubmitAdminOrder(id: string): Promise<AdminOrder> {
  const { data } = await apiClient.post<AdminOrder>(`/admin/orders/${id}/retry-submit/`);
  return data;
}

export interface BulkOrderActionPayload {
  order_ids: string[];
  action: "refund" | "retry";
  reason?: string;
}

export interface BulkOrderActionResult {
  detail: string;
  processed: number;
  skipped: { order: string; reason: string }[];
}

export async function bulkOrderAction(
  payload: BulkOrderActionPayload
): Promise<BulkOrderActionResult> {
  const { data } = await apiClient.post<BulkOrderActionResult>("/admin/orders/bulk-action/", payload);
  return data;
}
