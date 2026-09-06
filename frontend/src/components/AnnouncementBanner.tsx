import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Info, Megaphone, X } from "lucide-react";
import { useTranslation } from "react-i18next";

import { fetchAnnouncements } from "../api/endpoints/announcements";

const DISMISSED_KEY = "dismissed-announcements";

function readDismissed(): number[] {
  try {
    return JSON.parse(localStorage.getItem(DISMISSED_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function AnnouncementBanner() {
  const { t } = useTranslation();
  const [dismissed, setDismissed] = useState<number[]>(readDismissed);

  const { data } = useQuery({
    queryKey: ["announcements"],
    queryFn: fetchAnnouncements,
    staleTime: 5 * 60 * 1000,
  });

  function dismiss(id: number) {
    const next = [...dismissed, id];
    setDismissed(next);
    try {
      localStorage.setItem(DISMISSED_KEY, JSON.stringify(next));
    } catch {
      // A blocked storage API should never break the page.
    }
  }

  const visible = (data ?? []).filter((a) => !dismissed.includes(a.id));
  if (visible.length === 0) return null;

  return (
    <>
      {visible.map((announcement) => (
        <div
          key={announcement.id}
          className={`announcement-banner announcement-banner--${announcement.level}`}
        >
          {announcement.level === "info" ? <Info size={18} /> : <Megaphone size={18} />}
          <div>
            <strong>{announcement.title}</strong>
            <span>{announcement.body}</span>
          </div>
          {announcement.dismissible && (
            <button
              type="button"
              className="announcement-banner__dismiss"
              onClick={() => dismiss(announcement.id)}
              aria-label={t("common.dismiss")}
            >
              <X size={16} />
            </button>
          )}
        </div>
      ))}
    </>
  );
}
