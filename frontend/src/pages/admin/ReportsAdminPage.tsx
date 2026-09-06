import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  Activity,
  BookOpen,
  Download,
  Percent,
  PieChart,
  Receipt,
  TrendingDown,
  TrendingUp,
  Users,
  Wallet,
} from "lucide-react";

import {
  downloadCsv,
  fetchCategoryProfitability,
  fetchMarginDistribution,
  fetchReportSummary,
  fetchServiceMargins,
  fetchTopCustomers,
} from "../../api/endpoints/admin/reports";
import { formatMoney } from "../../utils/format";

/** Same 5 bands as apps.common.views_reports.AdminMarginDistributionView. */
const BAND_TONE: Record<string, string> = {
  loss: "status-badge--error",
  thin: "status-badge--pending",
  healthy: "status-badge--completed",
  strong: "status-badge--completed",
  premium: "status-badge--completed",
};

const RANGES = [
  { days: 7, label: "7 days" },
  { days: 30, label: "30 days" },
  { days: 90, label: "90 days" },
  { days: 365, label: "12 months" },
];

export function ReportsAdminPage() {
  const [days, setDays] = useState(30);
  const [downloading, setDownloading] = useState<string | null>(null);

  const { data: summary, isLoading } = useQuery({
    queryKey: ["report-summary", days],
    queryFn: () => fetchReportSummary(days),
  });
  const { data: margins } = useQuery({
    queryKey: ["report-margins", days],
    queryFn: () => fetchServiceMargins(days),
  });
  const { data: customers } = useQuery({
    queryKey: ["report-customers", days],
    queryFn: () => fetchTopCustomers(days),
  });
  const { data: profitability } = useQuery({
    queryKey: ["report-category-profitability", days],
    queryFn: () => fetchCategoryProfitability(days),
  });
  // Not date-ranged, so it doesn't need `days` in its key — it reflects the
  // catalogue as it's priced right now, not what sold in the chosen window.
  const { data: distribution } = useQuery({
    queryKey: ["report-margin-distribution"],
    queryFn: fetchMarginDistribution,
  });

  async function exportCsv(kind: "orders" | "ledger") {
    setDownloading(kind);
    try {
      await downloadCsv(kind, days);
    } finally {
      setDownloading(null);
    }
  }

  const peak = Math.max(1, ...(summary?.series ?? []).map((p) => Number(p.revenue)));

  return (
    <>
      <div className="page-header-row">
        <h1>Reports</h1>
        <div className="page-header-actions">
          <button
            className="btn-secondary btn-sm"
            onClick={() => exportCsv("orders")}
            disabled={downloading !== null}
          >
            <Download size={14} />
            {downloading === "orders" ? "Preparing…" : "Orders CSV"}
          </button>
          <button
            className="btn-secondary btn-sm"
            onClick={() => exportCsv("ledger")}
            disabled={downloading !== null}
          >
            <Download size={14} />
            {downloading === "ledger" ? "Preparing…" : "Ledger CSV"}
          </button>
        </div>
      </div>
      <p className="page-subtitle">
        Revenue is what customers paid after discounts. Cost is what the upstream provider charged.
        Refunded orders are excluded from both.
      </p>

      <div className="segmented">
        {RANGES.map((r) => (
          <button
            key={r.days}
            type="button"
            className={days === r.days ? "active" : ""}
            onClick={() => setDays(r.days)}
          >
            {r.label}
          </button>
        ))}
      </div>

      {isLoading && <p className="page-loading">Loading reports…</p>}

      {summary && (
        <>
          <div className="stat-grid">
            <ReportStat
              icon={<Wallet size={18} />}
              tone=""
              label="Revenue"
              value={formatMoney(summary.revenue)}
              sub={`${summary.order_count.toLocaleString()} orders`}
            />
            <ReportStat
              icon={<TrendingDown size={18} />}
              tone="icon-tile--warning"
              label="Provider cost"
              value={formatMoney(summary.cost)}
              sub="What we paid upstream"
            />
            <ReportStat
              icon={<TrendingUp size={18} />}
              tone="icon-tile--success"
              label="Profit"
              value={formatMoney(summary.profit)}
              sub={`${summary.margin_percent}% margin`}
            />
            <ReportStat
              icon={<Receipt size={18} />}
              tone="icon-tile--danger"
              label="Refunded"
              value={formatMoney(summary.refunded_amount)}
              sub={`${summary.refunded_count} orders`}
            />
          </div>

          <section className="panel">
            <div className="panel-header">
              <span className="icon-tile">
                <BookOpen size={18} />
              </span>
              <h2>Revenue by day</h2>
              <span className="panel-header__meta">
                Discounts given: {formatMoney(summary.discount_given)}
              </span>
            </div>
            {summary.series.length === 0 ? (
              <p className="muted mb-0">No orders in this period.</p>
            ) : (
              <div className="revenue-chart">
                {summary.series.map((point) => (
                  <div key={point.date} className="revenue-chart__col">
                    <div
                      className="revenue-chart__bar"
                      style={{ height: `${(Number(point.revenue) / peak) * 100}%` }}
                      title={`${point.date}: ${formatMoney(point.revenue)} revenue, ${formatMoney(
                        point.profit
                      )} profit`}
                    />
                    <span className="revenue-chart__label">{point.date.slice(5)}</span>
                  </div>
                ))}
              </div>
            )}
          </section>

          <div className="admin-dashboard-columns">
            <section className="panel">
              <div className="panel-header">
                <span className="icon-tile icon-tile--warning">
                  <Percent size={18} />
                </span>
                <h2>Service margins</h2>
                <span className="panel-header__meta">Worst first</span>
              </div>
              {!margins || margins.length === 0 ? (
                <p className="muted mb-0">No sales in this period.</p>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Service</th>
                        <th>Orders</th>
                        <th>Revenue</th>
                        <th>Profit</th>
                        <th>Margin</th>
                      </tr>
                    </thead>
                    <tbody>
                      {margins.slice(0, 25).map((row) => (
                        <tr key={row.service_id}>
                          <td>
                            {row.service_name}
                            <div className="text-sm muted">{row.category}</div>
                          </td>
                          <td>{row.orders}</td>
                          <td>{formatMoney(row.revenue)}</td>
                          <td
                            className={
                              Number(row.profit) < 0 ? "amount-negative" : "amount-positive"
                            }
                          >
                            {formatMoney(row.profit)}
                          </td>
                          <td>
                            <span
                              className={`status-badge ${
                                Number(row.margin_percent) < 0
                                  ? "status-badge--error"
                                  : Number(row.margin_percent) < 15
                                    ? "status-badge--pending"
                                    : "status-badge--completed"
                              }`}
                            >
                              {row.margin_percent}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="panel">
              <div className="panel-header">
                <span className="icon-tile icon-tile--info">
                  <Users size={18} />
                </span>
                <h2>Top customers</h2>
              </div>
              {!customers || customers.length === 0 ? (
                <p className="muted mb-0">No customers with orders in this period.</p>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Customer</th>
                        <th>Orders</th>
                        <th>Spent</th>
                      </tr>
                    </thead>
                    <tbody>
                      {customers.slice(0, 15).map((row) => (
                        <tr key={row.user_id}>
                          <td>{row.email}</td>
                          <td>{row.orders}</td>
                          <td>
                            <strong>{formatMoney(row.spent)}</strong>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>

          <section className="panel">
            <div className="panel-header">
              <span className="icon-tile icon-tile--info">
                <PieChart size={18} />
              </span>
              <h2>Profitability by platform</h2>
              <span className="panel-header__meta">Which platform actually makes you money</span>
            </div>
            {!profitability || profitability.platforms.length === 0 ? (
              <p className="muted mb-0">No sales in this period.</p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Platform</th>
                      <th>Orders</th>
                      <th>Revenue</th>
                      <th>Profit</th>
                      <th>Margin</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profitability.platforms.map((row) => (
                      <tr key={row.platform}>
                        <td style={{ textTransform: "capitalize" }}>{row.platform}</td>
                        <td>{row.orders}</td>
                        <td>{formatMoney(row.revenue)}</td>
                        <td className={Number(row.profit) < 0 ? "amount-negative" : "amount-positive"}>
                          {formatMoney(row.profit)}
                        </td>
                        <td>{row.margin_percent}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="panel">
            <div className="panel-header">
              <span className="icon-tile icon-tile--warning">
                <Activity size={18} />
              </span>
              <h2>Catalogue pricing health</h2>
              <span className="panel-header__meta">
                {distribution
                  ? `${distribution.total_priced_services.toLocaleString()} active services, priced right now`
                  : ""}
              </span>
            </div>
            {!distribution ? (
              <p className="muted mb-0">Loading…</p>
            ) : (
              <>
                <div className="margin-band-row">
                  {distribution.bands.map((band) => (
                    <div key={band.key} className="margin-band">
                      <span className={`status-badge ${BAND_TONE[band.key] ?? ""}`}>{band.label}</span>
                      <strong>{band.count.toLocaleString()}</strong>
                    </div>
                  ))}
                </div>
                {distribution.worst.length > 0 && (
                  <div className="table-wrap" style={{ marginTop: "1rem" }}>
                    <table>
                      <thead>
                        <tr>
                          <th>Service</th>
                          <th>Margin</th>
                        </tr>
                      </thead>
                      <tbody>
                        {distribution.worst.slice(0, 10).map((row) => (
                          <tr key={row.service_id}>
                            <td>
                              {row.service_name}
                              <div className="text-sm muted">{row.category}</div>
                            </td>
                            <td>
                              <span
                                className={`status-badge ${
                                  Number(row.margin_percent) < 0
                                    ? "status-badge--error"
                                    : "status-badge--pending"
                                }`}
                              >
                                {row.margin_percent}%
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </section>
        </>
      )}
    </>
  );
}

function ReportStat({
  icon,
  tone,
  label,
  value,
  sub,
}: {
  icon: React.ReactNode;
  tone: string;
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="stat-card">
      <div className="stat-card__top">
        <span className={`icon-tile ${tone}`}>{icon}</span>
        <span className="stat-card__label">{label}</span>
      </div>
      <span className="stat-card__value">{value}</span>
      <span className="stat-card__sublabel">{sub}</span>
    </div>
  );
}
