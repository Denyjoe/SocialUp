import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import { ar } from "./locales/ar";
import { en } from "./locales/en";
import { es } from "./locales/es";
import { fr } from "./locales/fr";
import { sw } from "./locales/sw";

/**
 * Supported languages shown in the language selector. Each entry carries a
 * native-script label so people can find their own language whatever the
 * current interface language is, and a direction so the layout can flip
 * for right-to-left scripts.
 */
export const SUPPORTED_LANGUAGES = [
  { code: "en", label: "English", dir: "ltr" },
  { code: "sw", label: "Kiswahili", dir: "ltr" },
  { code: "es", label: "Español", dir: "ltr" },
  { code: "fr", label: "Français", dir: "ltr" },
  { code: "ar", label: "العربية", dir: "rtl" },
] as const;

export type LanguageCode = (typeof SUPPORTED_LANGUAGES)[number]["code"];

const resources = {
  en: { translation: en },
  sw: { translation: sw },
  es: { translation: es },
  fr: { translation: fr },
  ar: { translation: ar },
};

function storedLanguage(): string {
  try {
    return localStorage.getItem("i18nextLng") || "en";
  } catch {
    return "en";
  }
}

/** Sets lang and dir on the html element, so Arabic lays out right to left
 * and screen readers announce the correct language. */
export function applyDocumentLanguage(code: string) {
  const entry = SUPPORTED_LANGUAGES.find((l) => l.code === code);
  document.documentElement.setAttribute("lang", code);
  document.documentElement.setAttribute("dir", entry?.dir ?? "ltr");
}

i18n.use(initReactI18next).init({
  resources,
  lng: storedLanguage(),
  fallbackLng: "en",
  // Keys are dotted for readability, not nested objects.
  keySeparator: false,
  nsSeparator: false,
  interpolation: { escapeValue: false },
});

applyDocumentLanguage(i18n.language);

i18n.on("languageChanged", (lng) => {
  try {
    localStorage.setItem("i18nextLng", lng);
  } catch {
    // A blocked storage API should not stop the language from changing.
  }
  applyDocumentLanguage(lng);
});

export default i18n;
