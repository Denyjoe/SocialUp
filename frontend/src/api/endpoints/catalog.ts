import { apiClient } from "../client";
import type { Category, Paginated, Service } from "../../types/api";

export async function fetchCategories(): Promise<Category[]> {
  const { data } = await apiClient.get<Category[]>("/catalog/categories/");
  return data;
}

export interface ServiceQuery {
  search?: string;
  category?: number | string;
  platform?: string;
  page?: number;
  page_size?: number;
}

/** Paginated and server-filtered. The catalog holds roughly 2,000 services,
 * so it is never fetched in full. */
export async function fetchServices(params: ServiceQuery = {}): Promise<Paginated<Service>> {
  const { data } = await apiClient.get<Paginated<Service>>("/catalog/services/", { params });
  return data;
}

/** Used to restore a service picked on the Services page when the customer
 * lands on New Order with `?service=<id>`. */
export async function fetchService(id: number | string): Promise<Service> {
  const { data } = await apiClient.get<Service>(`/catalog/services/${id}/`);
  return data;
}
