import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Activity,
  BarChart3,
  Server,
  ShoppingBag,
  TrendingUp,
  Trophy,
  Users,
  Wallet,
} from "lucide-react";

import { fetchDashboardStats, fetchRevenueTrend } from "../../api/endpoints/admin/dashboard";
import { RevenueTrendChart } from "../../components/RevenueTrendChart";
import { formatMoney } from "../../utils/format";

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  in_progress: "In progress",
  processing: "Processing",
  completed: "Completed",
  partial: "Partial",
  canceled: "Canceled",
  refunded: "Refunded",
  error: "Error",
};

export function DashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["admin", "dashboard-stats"],
    queryFn: fetchDashboardStats,
    refetchInterval: 60_000,
  });
  const { data: trend } = useQuery({
    queryKey: ["admin", "revenue-trend"],
    queryFn: () => fetchRevenueTrend(14),
  });

  if (isLoading || !stats) return <p className="page-loading">Loading dashboard…</p>;

  const profitToday = Number(stats.today.profit);
  const profitMonth = Number(stats.this_month.profit);

  return (
    <>
      <div className="page-header-row">
        <h1>Dashboard</h1>
        <div className="page-header-actions">
          <Link to="/admin/reports" className="btn btn-secondary btn-sm">
            <BarChart3 size={15} /> Full reports
          </Link>
        </div>
      </div>
      <p className="page-subtitle">A live view of how the business is doing today.</p>

      <div className="stat-grid">
        <AdminStat
          icon={<Wallet size={18} />}
          tone=""
          label="Revenue today"
          value={formatMoney(stats.today.revenue)}
          sub={`${stats.today.order_count} orders`}
        />
        <AdminStat
          icon={<TrendingUp size={18} />}
          tone={profitToday >= 0 ? "icon-tile--success" : "icon-tile--danger"}
          label="Profit today"
          value={formatMoney(stats.today.profit)}
          sub={profitToday >= 0 ? "In profit" : "At a loss"}
          negative={profitToday < 0}
        />
        <AdminStat
          icon={<Wallet size={18} />}
          tone="icon-tile--info"
          label="Revenue this month"
          value={formatMoney(stats.this_month.revenue)}
          sub={`${stats.this_month.order_count} orders`}
        />
        <AdminStat
          icon={<TrendingUp size={18} />}
          tone={profitMonth >= 0 ? "icon-tile--success" : "icon-tile--danger"}
          label="Profit this month"
          value={formatMoney(stats.this_month.profit)}
          sub={profitMonth >= 0 ? "In profit" : "At a loss"}
          negative={profitMonth < 0}
        />
        <AdminStat
          icon={<Users size={18} />}
          tone="icon-tile--info"
          label="Customers"
          value={stats.users.total.toLocaleString()}
          sub={`${stats.users.new_today} joined today`}
        />
        <AdminStat
          icon={<ShoppingBag size={18} />}
          tone=""
          label="Total orders"
          value={stats.orders.total.toLocaleString()}
          sub={`${stats.orders.today} today`}
        />
        <AdminStat
          icon={<Activity size={18} />}
          tone="icon-tile--warning"
          label="Wallet liability"
          value={formatMoney(stats.wallet_liability)}
          sub="Customer balances you hold"
        />
      </div>

      {trend && (
        <section className="panel">
          <div className="panel-header">
            <span className="icon-tile">
              <BarChart3 size={18} />
            </span>
            <h2>Revenue over the last 14 days</h2>
          </div>
          <RevenueTrendChart data={trend} />
        </section>
      )}

      <div className="admin-dashboard-columns">
        <section className="panel">
          <div className="panel-header">
            <span className="icon-tile icon-tile--info">
              <Trophy size={18} />
            </span>
            <h2>Top services this month</h2>
          </div>
          {stats.top_services_this_month.length === 0 ? (
            <p className="muted mb-0">No orders yet this month.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Service</th>
                    <th>Orders</th>
                    <th>Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.top_services_this_month.map((s) => (
                    <tr key={s.service_id}>
                      <td>{s.name}</td>
                      <td>{s.order_count}</td>
                      <td>
                        <strong>{formatMoney(s.revenue)}</strong>
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
            <span className="icon-tile">
              <ShoppingBag size={18} />
            </span>
            <h2>Orders by status</h2>
          </div>
          <div className="table-wrap">
            <table>
              <tbody>
                {Object.entries(stats.orders.by_status).map(([key, count]) => (
                  <tr key={key}>
                    <td>
                      <span className={`status-badge status-badge--${key}`}>
                        {STATUS_LABELS[key] ?? key}
                      </span>
                    </td>
                    <td>{count.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <section className="panel">
        <div className="panel-header">
          <span className="icon-tile icon-tile--warning">
            <Server size={18} />
          </span>
          <h2>Provider balances</h2>
          <Link to="/admin/providers" className="panel-header__meta">
            Manage providers
          </Link>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Provider</th>
                <th>Balance</th>
                <th>Last checked</th>
              </tr>
            </thead>
            <tbody>
              {stats.providers.map((p) => (
                <tr key={p.id}>
                  <td>
                    {p.name}{" "}
                    {!p.is_active && <span className="status-badge">Inactive</span>}
                  </td>
                  <td>
                    <strong>{formatMoney(p.balance_cached, p.balance_currency)}</strong>
                  </td>
                  <td className="muted nowrap">
                    {p.balance_last_checked_at
                      ? new Date(p.balance_last_checked_at).toLocaleString()
                      : "Never"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function AdminStat({
  icon,
  tone,
  label,
  value,
  sub,
  negative,
}: {
  icon: React.ReactNode;
  tone: string;
  label: string;
  value: string;
  sub: string;
  negative?: boolean;
}) {
  return (
    <div className={`stat-card${negative ? " stat-card--negative" : ""}`}>
      <div className="stat-card__top">
        <span className={`icon-tile ${tone}`}>{icon}</span>
        <span className="stat-card__label">{label}</span>
      </div>
      <span className="stat-card__value">{value}</span>
      <span className="stat-card__sublabel">{sub}</span>
    </div>
  );
}
