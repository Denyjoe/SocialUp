export type AnnouncementLevel = "info" | "success" | "warning";

export interface Announcement {
  id: number;
  title: string;
  body: string;
  level: AnnouncementLevel;
  dismissible: boolean;
  created_at: string;
}

export interface AdminAnnouncement extends Announcement {
  is_active: boolean;
  starts_at: string | null;
  ends_at: string | null;
  is_live: boolean;
  emailed_at: string | null;
  email_recipient_count: number;
  updated_at: string;
}
