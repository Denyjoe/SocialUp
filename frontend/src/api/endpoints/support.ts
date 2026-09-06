import { apiClient } from "../client";
import type { Ticket, TicketCategory, TicketDetail } from "../../types/support";
import type { Paginated } from "../../types/api";

export async function fetchTickets(): Promise<Ticket[]> {
  const { data } = await apiClient.get<Paginated<Ticket>>("/support/tickets/", {
    params: { page_size: 100 },
  });
  return data.results;
}

export async function fetchTicketDetail(id: number): Promise<TicketDetail> {
  const { data } = await apiClient.get<TicketDetail>(`/support/tickets/${id}/`);
  return data;
}

export interface CreateTicketPayload {
  subject: string;
  category: TicketCategory;
  message: string;
  order?: string;
}

export async function createTicket(payload: CreateTicketPayload): Promise<TicketDetail> {
  const { data } = await apiClient.post<TicketDetail>("/support/tickets/", payload);
  return data;
}

export async function addTicketMessage(ticketId: number, body: string) {
  const { data } = await apiClient.post(`/support/tickets/${ticketId}/messages/`, { body });
  return data;
}
