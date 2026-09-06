import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import {
  ArrowLeft,
  BarChart3,
  BookOpen,
  ChevronsLeft,
  ChevronsRight,
  Layers,
  LifeBuoy,
  LogOut,
  Megaphone,
  Percent,
  Receipt,
  Server,
  Settings,
  ShoppingBag,
  Tags,
  Users,
} from "lucide-react";

import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext";
import { UserMenu } from "../components/UserMenu";

const NAV_GROUPS: {
  headingKey: string;
  items: { to: string; labelKey: string; icon: typeof BarChart3; end?: boolean }[];
}[] = [
  {
    headingKey: "adminNav.overview",
    items: [
      { to: "/admin", labelKey: "adminNav.dashboard", icon: BarChart3, end: true },
      { to: "/admin/reports", labelKey: "adminNav.reports", icon: BookOpen },
    ],
  },
  {
    headingKey: "adminNav.operations",
    items: [
      { to: "/admin/orders", labelKey: "adminNav.orders", icon: ShoppingBag },
      { to: "/admin/services", labelKey: "adminNav.servicesPricing", icon: Layers },
      { to: "/admin/pricing-rules", labelKey: "adminNav.pricingRules", icon: Percent },
      { to: "/admin/providers", labelKey: "adminNav.providers", icon: Server },
    ],
  },
  {
    headingKey: "adminNav.customers",
    items: [
      { to: "/admin/users", labelKey: "adminNav.users", icon: Users },
      { to: "/admin/tickets", labelKey: "adminNav.supportTickets", icon: LifeBuoy },
      { to: "/admin/announcements", labelKey: "adminNav.announcements", icon: Megaphone },
    ],
  },
  {
    headingKey: "adminNav.money",
    items: [
      { to: "/admin/ledger", labelKey: "adminNav.walletLedger", icon: Receipt },
      { to: "/admin/coupons", labelKey: "adminNav.coupons", icon: Tags },
    ],
  },
  {
    headingKey: "adminNav.system",
    items: [{ to: "/admin/settings", labelKey: "adminNav.settings", icon: Settings }],
  },
];

export function AdminLayout() {
  const { t } = useTranslation();
  const { logout } = useAuth();
  const location = useLocation();

  const isDesktop = () => window.innerWidth >= 1024;
  const [navOpen, setNavOpen] = useState(() => isDesktop());
  const prevWidth = useRef(window.innerWidth);

  useEffect(() => {
    if (!isDesktop()) setNavOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    function handleResize() {
      const wasDesktop = prevWidth.current >= 1024;
      const nowDesktop = window.innerWidth >= 1024;
      prevWidth.current = window.innerWidth;
      if (!wasDesktop && nowDesktop) setNavOpen(true);
      if (wasDesktop && !nowDesktop) setNavOpen(false);
    }
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const toggleNav = () => setNavOpen((v) => !v);

  return (
    <div className={`app-shell admin-layout${navOpen && isDesktop() ? " sidebar-expanded" : ""}`}>
      <aside className={`sidebar${navOpen ? " is-open" : ""}`}>
        <div className="sidebar-header">
          <Link to="/admin" className="brand">
            <span className="brand__mark">
              <img className="brand__mark-img--light" src="/appicon.png" alt="" />
              <img className="brand__mark-img--dark" src="/appicon-dark.png" alt="" />
            </span>
            <span className="brand__label">SocialUp</span>
            <span className="admin-badge">{t("adminNav.badge")}</span>
          </Link>
        </div>
        <nav>
          {NAV_GROUPS.map((group) => (
            <div key={group.headingKey}>
              <div className="sidebar-section">{t(group.headingKey)}</div>
              {group.items.map(({ to, labelKey, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) => (isActive ? "active" : "")}
                >
                  <span className="nav-icon"><Icon size={18} /></span>
                  <span className="nav-label">{t(labelKey)}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <Link to="/dashboard" className="row">
            <span className="nav-icon"><ArrowLeft size={18} /></span>
            <span className="nav-label">{t("adminNav.customerDashboard")}</span>
          </Link>
          <button type="button" className="row" onClick={() => void logout()}>
            <span className="nav-icon"><LogOut size={18} /></span>
            <span className="nav-label">{t("account.signOut")}</span>
          </button>
        </div>
      </aside>

      {/* Floating collapse/expand handle. A sibling of <aside>, not a
          child of it — see the comment on .sidebar-toggle in index.css for
          why that placement actually matters, not just tidiness. */}
      <button
        type="button"
        className="sidebar-toggle"
        onClick={toggleNav}
        aria-label={navOpen ? t("nav.closeNavigation") : t("nav.openNavigation")}
        aria-expanded={navOpen}
      >
        <span className="sidebar-toggle__chip">
          {navOpen ? <ChevronsLeft size={16} /> : <ChevronsRight size={16} />}
        </span>
      </button>

      {navOpen && !isDesktop() && (
        <button
          type="button"
          className="sidebar-scrim"
          aria-label={t("nav.closeNavigation")}
          onClick={() => setNavOpen(false)}
        />
      )}

      <div className="dashboard-main">
        <header className="topbar">
          <div className="topbar__spacer" />
          <UserMenu />
        </header>
        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
