import { apiClient } from "../client";
import type { Announcement } from "../../types/announcements";

export async function fetchAnnouncements(): Promise<Announcement[]> {
  const { data } = await apiClient.get<Announcement[]>("/announcements/");
  return data;
}
