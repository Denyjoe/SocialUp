import { isAxiosError } from "axios";

/** Flattens a DRF error response ({"detail": "..."} or {"field": ["msg"]}) into one string. */
export function extractErrorMessage(error: unknown, fallback = "Something went wrong."): string {
  if (isAxiosError(error) && error.response?.data) {
    const data = error.response.data as Record<string, unknown>;
    if (typeof data.detail === "string") return data.detail;
    const messages = Object.values(data)
      .flat()
      .filter((v): v is string => typeof v === "string");
    if (messages.length) return messages.join(" ");
  }
  return fallback;
}
