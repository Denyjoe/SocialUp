import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Layers,
  Search,
  ChevronDown,
  Filter,
  Check,
  ShoppingCart,
  LayoutGrid,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import { Pagination } from "../../components/Pagination";
import { useMoney } from "../../currency/CurrencyContext";
import { useFitOneLine } from "../../hooks/useFitOneLine";
import { useServiceCatalog } from "../../hooks/useServiceCatalog";
import { resolvePlatformTheme } from "../../utils/platformTheme";

/** Number of services per page for pagination. */
const PAGE_SIZE = 25;

/**
 * Services page — professional SMM panel layout with a platform
 * filter grid, search, category dropdown, and grouped service cards.
 *
 * This page is shared between the public site (/services) and the
 * dashboard (/dashboard/services). The public `<main>` applies no
 * containment of its own, so the content needs the standard `.public-page`
 * container there. Inside the dashboard the app-shell's own main area
 * already centres and pads the content, so it must NOT get the wrapper.
 *
 * For a plain scannable price list instead of a browse-and-select grid,
 * see the public Pricing page, which renders the same underlying catalogue
 * (via `useServiceCatalog`) as a table.
 */
export function ServicesListPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();
  const money = useMoney();

  const inAppShell = location.pathname.startsWith("/dashboard") || location.pathname.startsWith("/admin");
  const pageClassName = inAppShell ? "" : "public-page";

  const [selectedId, setSelectedId] = useState<number | null>(null);

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
    grouped,
    uniquePlatforms,
    handlePlatformClick: catalogPlatformClick,
  } = useServiceCatalog(PAGE_SIZE);

  /** Toggling platform also clears any selected card, since it's likely gone from view. */
  function handlePlatformClick(id: string) {
    catalogPlatformClick(id);
    setSelectedId(null);
  }

  /** Jump to New Order with this service already chosen. */
  function orderService(id: number) {
    navigate(`/dashboard/new-order?service=${id}`);
  }

  const heroTitle = platform
    ? `${platform.charAt(0).toUpperCase() + platform.slice(1)} Services`
    : t("services.explore");
  // Shrinks to fit a long platform name on one line instead of wrapping
  // ("Instagram" / "Services" on separate lines) — see useFitOneLine.
  const heroTitleFit = useFitOneLine<HTMLHeadingElement>(heroTitle);

  return (
    <div className={pageClassName}>
      {/* ── Header ── */}
      <div className="svc-hero">
        <h1 className="svc-hero__title fit-one-line" ref={heroTitleFit.ref} style={heroTitleFit.style}>
          {heroTitle}
        </h1>
        <p className="svc-hero__sub">
          {t("services.exploreSub")}
        </p>
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
              <span
                className="platform-chip__icon"
                style={{ color: p.color }}
              >
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

      {!isLoading && grouped.length === 0 && (
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

      {/* ── Categorised card groups ── */}
      {grouped.map(([catName, { platform: catPlatform, services: catServices }]) => {
        const theme = resolvePlatformTheme(catPlatform, catName);
        const Icon = theme.icon;

        return (
          <section key={catName} className="svc-group">
            <div className="svc-group__header">
              <span
                className="svc-group__icon"
                style={{ background: theme.bg, color: theme.color }}
              >
                <Icon size={20} />
              </span>
              <h2 className="svc-group__title">{catName}</h2>
              <span className="badge">{catServices.length}</span>
            </div>

            <div className="svc-group__grid">
              {catServices.map((svc) => (
                <div
                  key={svc.id}
                  role="button"
                  tabIndex={0}
                  aria-pressed={selectedId === svc.id}
                  className={`svc-card${selectedId === svc.id ? " svc-card--selected" : ""}`}
                  onClick={() => setSelectedId(selectedId === svc.id ? null : svc.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setSelectedId(selectedId === svc.id ? null : svc.id);
                    }
                  }}
                >
                  <div className="svc-card__top">
                    <span
                      className="svc-card__dot"
                      style={{ background: theme.color }}
                    />
                    <div className="svc-card__name" title={svc.name}>
                      {svc.name}
                    </div>
                    {selectedId === svc.id && (
                      <span className="svc-card__check">
                        <Check size={14} />
                      </span>
                    )}
                  </div>

                  <div className="svc-card__rate">
                    <strong>{money(svc.retail_rate_per_1000)}</strong>
                    <span className="muted text-sm"> / 1K</span>
                  </div>

                  <div className="svc-card__meta">
                    <span>{t("common.min")}: {svc.min_quantity.toLocaleString()}</span>
                    <span>{t("common.max")}: {svc.max_quantity.toLocaleString()}</span>
                    {svc.average_time && (
                      <span className="muted">⏱ {svc.average_time}</span>
                    )}
                  </div>

                  {selectedId === svc.id ? (
                    <button
                      type="button"
                      className="svc-card__order btn-block"
                      onClick={(e) => {
                        // Do not let the click bubble back up and deselect.
                        e.stopPropagation();
                        orderService(svc.id);
                      }}
                    >
                      <ShoppingCart size={15} /> {t("services.orderThis")}
                    </button>
                  ) : (
                    <span className="svc-card__hint">{t("services.tapToSelect")}</span>
                  )}
                </div>
              ))}
            </div>
          </section>
        );
      })}

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
