import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, Coins, LayoutGrid, LifeBuoy, LogOut, Settings, Shield, Moon, Sun, Globe } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext";
import { SUPPORTED_LANGUAGES } from "../i18n";
import { useCurrency } from "../currency/CurrencyContext";
import { applyTheme, storedTheme } from "../theme";

/**
 * Top-bar user menu with account links, theme toggle, and language selector.
 */
export function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { t, i18n } = useTranslation();
  const { currency, setCurrency, supported, base } = useCurrency();
  const [theme, setTheme] = useState(storedTheme);

  /** main.tsx stamps the theme before first paint; this keeps the document
   * in step when the toggle is used. */
  useEffect(() => applyTheme(theme), [theme]);

  const toggleTheme = () => setTheme((prev) => (prev === "light" ? "dark" : "light"));

  /** Close menu on outside click or Escape. */
  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!user) return null;
  const initials = user.email.slice(0, 2);

  return (
    <div className="user-menu" ref={ref}>
      <button
        type="button"
        className="user-menu__trigger"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t("account.menu")}
      >
        <span className="avatar">{initials}</span>
        <span className="user-menu__email">{user.email}</span>
        <ChevronDown size={15} />
      </button>

      {open && (
        <div className="user-menu__dropdown" role="menu">
          <div className="user-menu__head">
            <strong>{user.is_staff ? t("account.administrator") : t("account.customer")}</strong>
            <span>{user.email}</span>
          </div>

          <Link to="/dashboard" onClick={() => setOpen(false)} role="menuitem">
            <LayoutGrid size={16} /> {t("nav.dashboard")}
          </Link>
          <Link to="/dashboard/settings" onClick={() => setOpen(false)} role="menuitem">
            <Settings size={16} /> {t("account.settings")}
          </Link>

          {/* ── Theme toggle ── */}
          <button type="button" onClick={toggleTheme} role="menuitem" className="user-menu__item-btn">
            {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
            {t("account.theme")}: {theme === "light" ? t("account.dark") : t("account.light")}
          </button>

          {/* ── Language selector (dropdown) ── */}
          <div className="user-menu__lang-row" role="menuitem">
            <Globe size={16} />
            <span>{t("account.language")}:</span>
            <select
              id="language-selector"
              value={i18n.language}
              onChange={(e) => i18n.changeLanguage(e.target.value)}
              className="user-menu__lang-select"
            >
              {SUPPORTED_LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.label}
                </option>
              ))}
            </select>
          </div>

          {/* Display currency. Conversion is for reading prices only:
              wallets and charges stay in the base currency. */}
          {supported.length > 1 && (
            <div className="user-menu__lang-row" role="menuitem">
              <Coins size={16} />
              <span>{t("account.currency")}:</span>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="user-menu__lang-select"
                aria-label={t("currency.displayIn")}
              >
                {supported.map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
              </select>
            </div>
          )}
          {currency !== base && (
            <p className="user-menu__note">{t("currency.approx", { base })}</p>
          )}

          <Link to="/dashboard/tickets" onClick={() => setOpen(false)} role="menuitem">
            <LifeBuoy size={16} /> {t("nav.support")}
          </Link>
          {user.is_staff && (
            <Link to="/admin" onClick={() => setOpen(false)} role="menuitem">
              <Shield size={16} /> {t("nav.adminArea")}
            </Link>
          )}

          <button type="button" className="user-menu__item-btn is-danger" onClick={() => void logout()} role="menuitem">
            <LogOut size={16} /> {t("account.signOut")}
          </button>
        </div>
      )}
    </div>
  );
}

