import { ChevronDown, Filter, HeartPulse, LayoutGrid, Search } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Pagination } from "../../components/Pagination";
import { useServiceCatalog } from "../../hooks/useServiceCatalog";
import type { Service } from "../../types/api";

/** Rows are compact, same as the Pricing page. */
const PAGE_SIZE = 30;

/** >15% refill rate reads as unhealthy, <=5% as healthy, in between as
 * watch-worthy. Thresholds are a judgment call, not a provider-given
 * standard — refill rate is itself a proxy for drops (see health.py),
 * so these bands are intentionally generous rather than alarmist. */
function refillTone(percent: number): string {
  if (percent <= 5) return "status-badge--completed";
  if (percent <= 15) return "status-badge--pending";
  return "status-badge--error";
}

function formatStart(minutes: string): string {
  const value = Number(minutes);
  if (value < 60) return `~${Math.round(value)} min`;
  return `~${(value / 60).toFixed(1)} hr`;
}

/**
 * Public Service Health dashboard — the transparency play: buyers can see
 * average start time, delivery speed, and a refill-rate proxy for every
 * service over the last 48h, before they ever place an order. Same
 * platform/search/category filters as Services and Pricing (all three
 * share `useServiceCatalog`), but each row reads from the cached
 * `Service.health` rollup rather than pricing data.
 */
export function ServiceHealthPage() {
  const { t } = useTranslation();

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

  return (
    <div className="public-page">
      {/* ── Header ── */}
      <div className="svc-hero">
        <h1 className="svc-hero__title">
          {platform
            ? t("serviceHealth.platformTitle", { platform: platform.charAt(0).toUpperCase() + platform.slice(1) })
            : t("serviceHealth.title")}
        </h1>
        <p className="svc-hero__sub">{t("serviceHealth.sub")}</p>
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

      <p className="muted text-sm" style={{ margin: "-0.5rem 0 1rem" }}>
        {t("serviceHealth.refreshedHourly")}
      </p>

      {/* ── States ── */}
      {isError && <p className="form-error">{t("services.couldNotLoad")}</p>}
      {isLoading && <p className="page-loading">{t("common.loading")}</p>}

      {!isLoading && services.length === 0 && (
        <div className="panel">
          <div className="empty-state">
            <span className="empty-state__icon">
              <HeartPulse size={22} />
            </span>
            <h3>{t("services.notFound")}</h3>
            <p>{t("services.notFoundBody")}</p>
          </div>
        </div>
      )}

      {services.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("serviceHealth.colService")}</th>
                <th>{t("serviceHealth.colStart")}</th>
                <th>{t("serviceHealth.colSpeed")}</th>
                <th>{t("serviceHealth.colRefill")}</th>
                <th>{t("serviceHealth.colSamples")}</th>
              </tr>
            </thead>
            <tbody>
              {services.map((service) => (
                <ServiceHealthRow key={service.id} service={service} />
              ))}
            </tbody>
          </table>
        </div>
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

function ServiceHealthRow({ service }: { service: Service }) {
  const { t } = useTranslation();
  const health = service.health;
  const nameCell = (
    <td>
      <div title={service.name}>{service.name}</div>
      <div className="muted text-sm">{service.category.name}</div>
    </td>
  );

  if (health === null || health.avg_speed_per_hour === null) {
    return (
      <tr>
        {nameCell}
        <td colSpan={3} className="muted text-sm">
          {t("serviceHealth.notEnoughData")}
        </td>
        <td className="muted text-sm">
          {t("serviceHealth.sampleCount", { count: health?.sample_size ?? 0 })}
        </td>
      </tr>
    );
  }

  return (
    <tr>
      {nameCell}
      <td>{health.avg_start_minutes !== null ? formatStart(health.avg_start_minutes) : "—"}</td>
      <td>
        {t("serviceHealth.speedValue", {
          value: Math.round(Number(health.avg_speed_per_hour)).toLocaleString(),
        })}
      </td>
      <td>
        {health.refill_rate_percent !== null ? (
          <span className={`status-badge ${refillTone(Number(health.refill_rate_percent))}`}>
            {Number(health.refill_rate_percent).toFixed(1)}%
          </span>
        ) : (
          "—"
        )}
      </td>
      <td className="muted text-sm">{t("serviceHealth.sampleCount", { count: health.sample_size })}</td>
    </tr>
  );
}
