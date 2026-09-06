export type TicketStatus = "open" | "answered" | "pending" | "closed";
export type TicketCategory = "general" | "billing" | "order_issue" | "technical" | "other";
export type TicketPriority = "low" | "normal" | "high" | "urgent";

export interface TicketMessage {
  id: number;
  sender_email: string;
  is_staff_reply: boolean;
  body: string;
  attachment_url: string | null;
  created_at: string;
}

export interface Ticket {
  id: number;
  subject: string;
  category: TicketCategory;
  status: TicketStatus;
  priority: TicketPriority;
  order: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface TicketDetail extends Ticket {
  messages: TicketMessage[];
}
