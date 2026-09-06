import { Link } from "react-router-dom";
import { ArrowRight, ChevronDown, Filter, LayoutGrid, Layers, Search } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../../auth/AuthContext";
import { useMoney } from "../../currency/CurrencyContext";
import { useServiceCatalog } from "../../hooks/useServiceCatalog";
import { Pagination } from "../../components/Pagination";
import { resolvePlatformTheme } from "../../utils/platformTheme";

/** Rows are compact, so a page holds more of them than the Services card grid. */
const PAGE_SIZE = 30;

/**
 * Pricing page — a plain, scannable price list across the whole catalogue:
 * same platform/search/category filters as the Services page (both are
 * powered by the shared `useServiceCatalog` hook, so the numbers never
 * drift apart), but presented as a table to browse and compare rather
 * than cards to pick and configure. Order actions jump straight into an
 * order, since there is nothing to "select" first here.
 */
export function PricingPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const money = useMoney();

  const {
    platform,
    term,
    setTerm,
    category,
    setCategory,
    page,
    setPage,
    categories,
    data,
    isLoading,
    isError,
    services,
    uniquePlatforms,
    handlePlatformClick,
  } = useServiceCatalog(PAGE_SIZE);

  /** Signed-in visitors go straight to the order form with this service
   * preselected; everyone else registers first. */
  function orderHref(serviceId: number): string {
    return user ? `/dashboard/new-order?service=${serviceId}` : "/register";
  }

  return (
    <div className="public-page">
      {/* ── Header ── */}
      <div className="svc-hero">
        <h1 className="svc-hero__title">
          {platform
            ? t("pricing.platformTitle", { platform: platform.charAt(0).toUpperCase() + platform.slice(1) })
            : t("pricing.title")}
        </h1>
        <p className="svc-hero__sub">{t("pricing.sub")}</p>
      </div>

      {/* ── Platform buttons ── */}
      <div className="platform-grid">
        <button
          className={`platform-chip${platform === "" ? " platform-chip--active" : ""}`}
          onClick={() => handlePlatformClick(platform)}
          aria-pressed={platform === ""}
        >
          <span className="platform-chip__icon" style={{ color: "var(--primary)" }}>
            <LayoutGrid size={20} />
          </span>
          <span className="platform-chip__label">{t("common.all")}</span>
        </button>

        {uniquePlatforms.map((p) => {
          const Icon = p.icon;
          const isActive = platform === p.id;
          return (
            <button
              key={p.id}
              className={`platform-chip${isActive ? " platform-chip--active" : ""}`}
              onClick={() => handlePlatformClick(p.id)}
              aria-pressed={isActive}
              style={
                isActive
                  ? ({ "--chip-accent": p.color, "--chip-accent-bg": p.bg } as React.CSSProperties)
                  : undefined
              }
            >
              <span className="platform-chip__icon" style={{ color: p.color }}>
                <Icon size={20} />
              </span>
              <span className="platform-chip__label">{p.name}</span>
            </button>
          );
        })}
      </div>

      {/* ── Search + Category filter ── */}
      <div className="svc-toolbar">
        <div className="svc-toolbar__search">
          <Search size={18} className="svc-toolbar__search-icon" />
          <input
            type="text"
            placeholder={t("services.searchPlaceholder")}
            value={term}
            onChange={(e) => setTerm(e.target.value)}
          />
        </div>

        <div className="svc-toolbar__select-wrap">
          <Filter size={15} className="svc-toolbar__select-pre" />
          <select
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setPage(1);
            }}
          >
            <option value="">{t("services.allCategories")}</option>
            {categories
              ?.filter((c) => {
                if (!platform) return true;
                const platformMatch = c.platform && c.platform.toLowerCase() === platform;
                const nameMatch = c.name.toLowerCase().includes(platform);
                return platformMatch || nameMatch;
              })
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
          </select>
          <ChevronDown size={16} className="svc-toolbar__select-chevron" />
        </div>

        <span className="svc-toolbar__count badge">
          {t("services.count", { count: data?.count ?? 0 })}
        </span>
      </div>

      {/* ── States ── */}
      {isError && <p className="form-error">{t("services.couldNotLoad")}</p>}
      {isLoading && <p className="page-loading">{t("common.loading")}</p>}

      {!isLoading && services.length === 0 && (
        <div className="panel">
          <div className="empty-state">
            <span className="empty-state__icon">
              <Layers size={22} />
            </span>
            <h3>{t("services.notFound")}</h3>
            <p>{t("services.notFoundBody")}</p>
          </div>
        </div>
      )}

      {services.length > 0 && (
        <>
          {/* Cards on narrow screens; a real table takes over from 780px up
              (CSS toggles which one renders). Same rows, two presentations. */}
          <div className="lp-price-grid">
            {services.map((service) => (
              <div className="lp-price-card" key={service.id}>
                <span className="badge">{service.category.name}</span>
                <h3 title={service.name}>{service.name}</h3>
                <div className="lp-price-card__rate">
                  <strong>{money(service.retail_rate_per_1000)}</strong>
                  <span className="muted"> {t("common.perThousand")}</span>
                </div>
                <div className="lp-price-card__meta">
                  <span>{t("common.min")} {service.min_quantity.toLocaleString()}</span>
                  <span>{t("common.max")} {service.max_quantity.toLocaleString()}</span>
                </div>
                <Link to={orderHref(service.id)} className="btn btn-secondary btn-sm lp-price-card__order">
                  {t("nav.order")} <ArrowRight size={14} />
                </Link>
              </div>
            ))}
          </div>

          <div className="lp-pricing-table-wrap">
            <table className="lp-pricing-table">
              <thead>
                <tr>
                  <th>{t("landing.tableService")}</th>
                  <th>{t("landing.tablePrice")}</th>
                  <th>{t("landing.tableQuantity")}</th>
                  <th>{t("landing.tableDelivery")}</th>
                  <th>{t("common.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {services.map((service) => {
                  const theme = resolvePlatformTheme(
                    service.category.platform || service.category.name,
                    service.name
                  );
                  return (
                    <tr key={service.id}>
                      <td>
                        <div className="lp-pricing-table__service">
                          <span className="lp-pricing-table__badge" style={{ background: theme.color }}>
                            <theme.icon />
                          </span>
                          <span title={service.name}>{service.name}</span>
                        </div>
                      </td>
                      <td className="lp-pricing-table__price">
                        {money(service.retail_rate_per_1000)} <small>/ 1,000</small>
                      </td>
                      <td className="lp-pricing-table__meta">
                        {service.min_quantity.toLocaleString()} – {service.max_quantity.toLocaleString()}
                      </td>
                      <td className="lp-pricing-table__meta">
                        {service.average_time || t("landing.deliveryVaries")}
                      </td>
                      <td>
                        <Link to={orderHref(service.id)} className="lp-pricing-table__order">
                          {t("nav.order")} <ArrowRight size={13} />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}

      {(data?.count ?? 0) > PAGE_SIZE && (
        <Pagination
          page={page}
          count={data?.count ?? 0}
          pageSize={PAGE_SIZE}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
