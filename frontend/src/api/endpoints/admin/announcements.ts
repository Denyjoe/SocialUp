import { apiClient } from "../../client";
import type { AdminAnnouncement } from "../../../types/announcements";
import type { Paginated } from "../../../types/api";

export interface AnnouncementPayload {
  title: string;
  body: string;
  level: string;
  is_active: boolean;
  dismissible: boolean;
  starts_at?: string | null;
  ends_at?: string | null;
}

export async function fetchAdminAnnouncements(): Promise<Paginated<AdminAnnouncement>> {
  const { data } = await apiClient.get<Paginated<AdminAnnouncement>>("/admin/announcements/");
  return data;
}

export async function createAnnouncement(payload: AnnouncementPayload): Promise<AdminAnnouncement> {
  const { data } = await apiClient.post<AdminAnnouncement>("/admin/announcements/", payload);
  return data;
}

export async function updateAnnouncement(
  id: number,
  payload: Partial<AnnouncementPayload>
): Promise<AdminAnnouncement> {
  const { data } = await apiClient.patch<AdminAnnouncement>(`/admin/announcements/${id}/`, payload);
  return data;
}

export async function deleteAnnouncement(id: number): Promise<void> {
  await apiClient.delete(`/admin/announcements/${id}/`);
}

export async function sendAnnouncementEmail(id: number): Promise<{ detail: string }> {
  const { data } = await apiClient.post(`/admin/announcements/${id}/send-email/`);
  return data;
}
