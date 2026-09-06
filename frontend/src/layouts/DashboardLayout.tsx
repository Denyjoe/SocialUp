import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import {
  BarChart3,
  ChevronsLeft,
  ChevronsRight,
  Code2,
  LifeBuoy,
  Layers,
  ListOrdered,
  LogOut,
  PlusCircle,
  Settings,
  Share2,
  Shield,
  ShoppingBag,
  Wallet,
} from "lucide-react";

import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext";
import { AnnouncementBanner } from "../components/AnnouncementBanner";
import { UserMenu } from "../components/UserMenu";
import { VerificationBanner } from "../components/VerificationBanner";
import { WalletBalanceWidget } from "../components/WalletBalanceWidget";

const NAV_ITEMS = [
  { to: "/dashboard",             label: "nav.dashboard",   icon: BarChart3,   end: true },
  { to: "/dashboard/new-order",   label: "nav.newOrder",    icon: PlusCircle },
  { to: "/dashboard/services",    label: "nav.services",    icon: Layers },
  { to: "/dashboard/bulk-order",  label: "nav.bulkOrder",   icon: ListOrdered },
  { to: "/dashboard/orders",      label: "nav.orderHistory",icon: ShoppingBag },
  { to: "/dashboard/add-funds",   label: "nav.addFunds",    icon: Wallet },
  { to: "/dashboard/affiliate",   label: "nav.affiliate",   icon: Share2 },
  { to: "/dashboard/tickets",     label: "nav.support",     icon: LifeBuoy },
  { to: "/dashboard/api",         label: "nav.api",         icon: Code2 },
  { to: "/dashboard/settings",    label: "nav.settings",    icon: Settings },
];

/** Five tabs shown in the bottom navigation bar on mobile. */
const BOTTOM_NAV = [
  { to: "/dashboard",           label: "nav.home",    icon: BarChart3,  end: true },
  { to: "/dashboard/new-order", label: "nav.order",   icon: PlusCircle },
  { to: "/dashboard/orders",    label: "nav.history", icon: ShoppingBag },
  { to: "/dashboard/add-funds", label: "nav.funds",   icon: Wallet },
  { to: "/dashboard/tickets",   label: "nav.support", icon: LifeBuoy },
];

export function DashboardLayout() {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  const location = useLocation();

  /**
   * On mobile: navOpen drives the drawer overlay.
   * On desktop (≥1024px): navOpen drives whether the sidebar is expanded
   * (true) or collapsed to a slim icon-only rail (false).
   * We start expanded on desktop, closed on mobile.
   */
  const isDesktop = () => window.innerWidth >= 1024;
  const [navOpen, setNavOpen] = useState(() => isDesktop());
  const prevWidth = useRef(window.innerWidth);

  // Close the mobile drawer whenever the route changes.
  useEffect(() => {
    if (!isDesktop()) setNavOpen(false);
  }, [location.pathname]);

  // When the window crosses the 1024px breakpoint, reset to the
  // appropriate default so there is no flash of wrong state.
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
    <div className={`app-shell${navOpen && isDesktop() ? " sidebar-expanded" : ""}`}>

      {/* ── Sidebar ── */}
      <aside className={`sidebar${navOpen ? " is-open" : ""}`}>
        <div className="sidebar-header">
          <Link to="/" className="brand">
            <span className="brand__mark">
              <img className="brand__mark-img--light" src="/appicon.png" alt="" />
              <img className="brand__mark-img--dark" src="/appicon-dark.png" alt="" />
            </span>
            <span className="brand__label">SocialUp</span>
          </Link>
        </div>

        {/* Navigation */}
        <nav>
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              <span className="nav-icon"><Icon size={18} /></span>
              <span className="nav-label">{t(label)}</span>
            </NavLink>
          ))}
          {user?.is_staff && (
            <>
              <div className="sidebar-section">{t("nav.staff")}</div>
              <NavLink
                to="/admin"
                className={({ isActive }) => (isActive ? "active" : "")}
              >
                <span className="nav-icon"><Shield size={18} /></span>
                <span className="nav-label">{t("nav.adminArea")}</span>
              </NavLink>
            </>
          )}
        </nav>

        <div className="sidebar-footer">
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

      {/* ── Mobile scrim (closes sidebar when tapped) ── */}
      {navOpen && !isDesktop() && (
        <button
          type="button"
          className="sidebar-scrim"
          aria-label={t("nav.closeNavigation")}
          onClick={() => setNavOpen(false)}
        />
      )}

      {/* ── Main content ── */}
      <div className="dashboard-main">
        <header className="topbar">
          <div className="topbar__spacer" />
          <WalletBalanceWidget />
          <UserMenu />
        </header>

        <main>
          <AnnouncementBanner />
          <VerificationBanner />
          <Outlet />
        </main>
      </div>

      {/* ── Bottom nav (mobile only) ── */}
      <nav className="bottom-nav">
        {BOTTOM_NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            <Icon size={19} />
            {t(label)}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
