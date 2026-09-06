import { apiClient } from "../../client";
import type { Paginated } from "../../../types/api";
import type { TicketDetail, TicketStatus } from "../../../types/support";

export interface AdminTicket extends Omit<TicketDetail, "messages"> {
  user_email: string;
}

export interface AdminTicketDetail extends AdminTicket {
  messages: TicketDetail["messages"];
}

export interface AdminTicketListParams {
  page?: number;
  status?: string;
  user?: string;
}

export async function fetchAdminTickets(params: AdminTicketListParams): Promise<Paginated<AdminTicket>> {
  const { data } = await apiClient.get<Paginated<AdminTicket>>("/admin/tickets/", { params });
  return data;
}

export async function fetchAdminTicketDetail(id: number): Promise<AdminTicketDetail> {
  const { data } = await apiClient.get<AdminTicketDetail>(`/admin/tickets/${id}/`);
  return data;
}

export async function replyToTicket(id: number, body: string): Promise<AdminTicketDetail> {
  const { data } = await apiClient.post<AdminTicketDetail>(`/admin/tickets/${id}/reply/`, { body });
  return data;
}

export async function setTicketStatus(id: number, status: TicketStatus): Promise<AdminTicket> {
  const { data } = await apiClient.post<AdminTicket>(`/admin/tickets/${id}/status/`, { status });
  return data;
}
