import { apiClient } from "../client";
import type { Order, Paginated } from "../../types/api";

export interface CreateOrderPayload {
  service: number;
  link: string;
  quantity: number;
  coupon_code?: string;
}

export async function createOrder(payload: CreateOrderPayload): Promise<Order> {
  const { data } = await apiClient.post<Order>("/orders/", payload);
  return data;
}

export async function fetchOrders(): Promise<Order[]> {
  const { data } = await apiClient.get<Paginated<Order>>("/orders/", {
    params: { page_size: 100 },
  });
  return data.results;
}

export interface BulkOrderLine {
  service: number;
  link: string;
  quantity: number;
}

export interface BulkOrderResult {
  success: boolean;
  order?: Order;
  error?: string;
}

/** Each line is charged and submitted independently server-side — a bad
 * line never blocks the rest, so the response is always 200 with a
 * per-line result even when some lines failed. */
export async function bulkCreateOrders(lines: BulkOrderLine[]): Promise<BulkOrderResult[]> {
  const { data } = await apiClient.post<{ results: BulkOrderResult[] }>("/orders/bulk/", {
    orders: lines,
  });
  return data.results;
}
