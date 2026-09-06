import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Globe, Menu, Moon, Sun, X } from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import { SUPPORTED_LANGUAGES } from "../i18n";
import { applyTheme, storedTheme } from "../theme";
import { useTranslation } from "react-i18next";

const LINKS = [
  { to: "/services", label: "nav.services" },
  { to: "/pricing", label: "nav.pricing" },
  { to: "/service-health", label: "nav.serviceHealth" },
  { to: "/api-docs", label: "nav.api" },
];

export function PublicLayout() {
  const { user } = useAuth();
  const { t, i18n } = useTranslation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [theme, setTheme] = useState(storedTheme);
  const location = useLocation();

  useEffect(() => setMenuOpen(false), [location.pathname]);
  useEffect(() => applyTheme(theme), [theme]);

  return (
    <div className="public-layout">
      <header className="public-nav">
        <Link to="/" className="brand">
          <span className="brand__mark">
            <img className="brand__mark-img--light" src="/appicon.png" alt="" />
            <img className="brand__mark-img--dark" src="/appicon-dark.png" alt="" />
          </span>
          SocialUp
        </Link>

        <nav className="public-nav__links">
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to}>
              {t(link.label)}
            </NavLink>
          ))}
        </nav>

        <div className="public-nav__actions">
          {/* Visitors are not signed in, so the user menu is not there to
              carry the language selector. */}
          <label className="public-nav__lang">
            <Globe size={15} aria-hidden="true" />
            <span className="sr-only">{t("nav.language")}</span>
            <select
              value={i18n.language}
              onChange={(e) => void i18n.changeLanguage(e.target.value)}
              aria-label={t("nav.language")}
            >
              {SUPPORTED_LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="btn-ghost btn-icon"
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            aria-label={`${t("account.theme")}: ${
              theme === "light" ? t("account.dark") : t("account.light")
            }`}
          >
            {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
          </button>
          {/* Hidden below 860px — crammed in next to the language switcher,
              theme toggle and hamburger, "Log in" was the first label to
              run out of room and wrap onto two lines. The same links live
              in the mobile drawer below instead, where there's room. */}
          <div className="public-nav__auth">
            {user ? (
              <Link to="/dashboard" className="btn btn-sm">
                {t("nav.dashboard")}
              </Link>
            ) : (
              <>
                <Link to="/login" className="btn btn-secondary btn-sm">
                  {t("nav.logIn")}
                </Link>
                <Link to="/register" className="btn btn-sm">
                  {t("nav.register")}
                </Link>
              </>
            )}
          </div>
          <button
            type="button"
            className="btn-ghost btn-icon public-nav__toggle"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? t("nav.closeNavigation") : t("nav.openNavigation")}
            aria-expanded={menuOpen}
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </header>

      {menuOpen && (
        <div className="public-nav__mobile">
          {LINKS.map((link) => (
            <Link key={link.to} to={link.to}>
              {t(link.label)}
            </Link>
          ))}
          <div className="public-nav__mobile-auth">
            {user ? (
              <Link to="/dashboard" className="btn btn-sm btn-block">
                {t("nav.dashboard")}
              </Link>
            ) : (
              <>
                <Link to="/login" className="btn btn-secondary btn-sm">
                  {t("nav.logIn")}
                </Link>
                <Link to="/register" className="btn btn-sm">
                  {t("nav.register")}
                </Link>
              </>
            )}
          </div>
        </div>
      )}

      <main>
        <Outlet />
      </main>

      <footer className="public-footer">
        <div className="lp-footer">
          <div className="lp-footer__brand">
            <span className="brand">
              <span className="brand__mark">
                <img className="brand__mark-img--light" src="/appicon.png" alt="" />
                <img className="brand__mark-img--dark" src="/appicon-dark.png" alt="" />
              </span>
              SocialUp
            </span>
            <p>
              {t("landing.footerBlurb")}
            </p>
          </div>

          <div className="lp-footer__col">
            <h4>{t("landing.footerProduct")}</h4>
            <Link to="/services">{t("nav.services")}</Link>
            <Link to="/pricing">{t("nav.pricing")}</Link>
            <Link to="/service-health">{t("nav.serviceHealth")}</Link>
            <Link to="/api-docs">{t("nav.api")}</Link>
          </div>

          <div className="lp-footer__col">
            <h4>{t("landing.footerAccount")}</h4>
            <Link to="/register">{t("auth.createAccount")}</Link>
            <Link to="/login">{t("auth.logIn")}</Link>
            <Link to="/forgot-password">{t("landing.footerResetPassword")}</Link>
          </div>

          <div className="lp-footer__col">
            <h4>{t("landing.footerSupport")}</h4>
            <Link to="/dashboard/tickets">{t("landing.footerOpenTicket")}</Link>
            <Link to="/api-docs">{t("landing.footerDocs")}</Link>
          </div>
        </div>

        <div className="lp-footer__base">
          <span>© {new Date().getFullYear()} SocialUp. {t("landing.footerRights")}</span>
          <span>{t("landing.footerNoPassword")}</span>
        </div>
      </footer>
    </div>
  );
}
