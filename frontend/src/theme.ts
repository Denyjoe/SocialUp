/**
 * Theme is stamped on the document element, not held in React state, because
 * it has to be right on the very first paint and on every route. The user
 * menu that used to own this only renders inside the dashboard, so a saved
 * dark-mode choice was silently ignored on the landing and auth pages.
 */

const STORAGE_KEY = "theme";

export type Theme = "light" | "dark";

export function storedTheme(): Theme {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    // A blocked storage API should not stop the app rendering.
  }
  // No choice made yet, so follow the operating system.
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Persisting is a convenience; the attribute is what actually matters.
  }
}

/** Called once at startup, before React mounts. */
export function initTheme() {
  document.documentElement.setAttribute("data-theme", storedTheme());
}
