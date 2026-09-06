import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  PlusCircle,
  ShoppingBag,
  Wallet,
} from "lucide-react";

import { fetchOrders } from "../../api/endpoints/orders";
import { fetchWallet } from "../../api/endpoints/wallet";
import { useAuth } from "../../auth/AuthContext";
import { OrderStatusBadge } from "../../components/OrderStatusBadge";
import { useMoney } from "../../currency/CurrencyContext";
import { useFitOneLine } from "../../hooks/useFitOneLine";
import { useTranslation } from "react-i18next";

export function DashboardHome() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const money = useMoney();
  const { data: wallet } = useQuery({ queryKey: ["wallet"], queryFn: fetchWallet });
  const { data: orders } = useQuery({ queryKey: ["orders"], queryFn: fetchOrders });

  const all = orders ?? [];
  const completed = all.filter((o) => o.status === "completed");
  const active = all.filter((o) => ["pending", "in_progress", "processing"].includes(o.status));
  const totalSpent = all
    .filter((o) => o.status !== "refunded")
    .reduce((sum, o) => sum + Number(o.charge_amount), 0);

  const firstName = user?.email.split("@")[0] ?? "there";
  const greeting = t("home.welcome", { name: firstName });
  // Shrinks to fit a long name on one line instead of wrapping or cutting
  // it off with an ellipsis — see useFitOneLine for why.
  const greetingFit = useFitOneLine<HTMLHeadingElement>(greeting);

  return (
    <>
      <div className="page-header-row">
        <div className="page-header-row__text">
          <h1 className="fit-one-line" ref={greetingFit.ref} style={greetingFit.style}>
            {greeting}
          </h1>
          <p className="page-subtitle mb-0">
            {t("home.subtitle")}
          </p>
        </div>
        <div className="page-header-actions">
          <Link to="/dashboard/new-order" className="btn">
            <PlusCircle size={16} /> {t("nav.newOrder")}
          </Link>
        </div>
      </div>

      <div className="stat-grid">
        <StatTile
          icon={<Wallet size={18} />}
          tone=""
          label={t("wallet.walletBalance")}
          value={wallet ? money(wallet.cached_balance) : "…"}
          actionLabel={t("wallet.addFunds")}
          to="/dashboard/add-funds"
        />
        <StatTile
          icon={<ShoppingBag size={18} />}
          tone="icon-tile--info"
          label={t("home.totalOrders")}
          value={all.length.toLocaleString()}
          actionLabel={t("home.viewHistory")}
          to="/dashboard/orders"
        />
        <StatTile
          icon={<CheckCircle2 size={18} />}
          tone="icon-tile--success"
          label={t("home.completed")}
          value={completed.length.toLocaleString()}
          actionLabel={t("home.viewHistory")}
          to="/dashboard/orders"
        />
        <StatTile
          icon={<Clock size={18} />}
          tone="icon-tile--warning"
          label={t("home.totalSpent")}
          value={money(totalSpent)}
          actionLabel={t("home.browseServices")}
          to="/dashboard/services"
        />
      </div>

      <section className="panel">
        <div className="panel-header">
          <span className="icon-tile">
            <ShoppingBag size={18} />
          </span>
          <h2>{t("home.recentOrders")}</h2>
          <Link to="/dashboard/orders" className="panel-header__meta">
            {t("home.viewAll")}
          </Link>
        </div>

        {all.length === 0 ? (
          <div className="empty-state">
            <span className="empty-state__icon">
              <PlusCircle size={22} />
            </span>
            <h3>{t("home.noOrders")}</h3>
            <p>{t("home.noOrdersBody")}</p>
            <Link to="/dashboard/new-order" className="btn">
              {t("home.placeFirstOrder")} <ArrowRight size={15} />
            </Link>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("orders.service")}</th>
                  <th>{t("orders.quantity")}</th>
                  <th>{t("orders.charged")}</th>
                  <th>{t("common.status")}</th>
                  <th>{t("orders.placed")}</th>
                </tr>
              </thead>
              <tbody>
                {all.slice(0, 6).map((order) => (
                  <tr key={order.id}>
                    <td>{order.service_name}</td>
                    <td>{order.quantity.toLocaleString()}</td>
                    <td>{money(order.charge_amount)}</td>
                    <td>
                      <OrderStatusBadge status={order.status} />
                    </td>
                    <td className="muted">{new Date(order.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {active.length > 0 && (
        <section className="panel">
          <div className="panel-header">
            <span className="icon-tile icon-tile--warning">
              <Clock size={18} />
            </span>
            <h2>{t("home.inProgress")}</h2>
          </div>
          <p className="muted mb-0">
            {t("home.inProgressBody", { count: active.length })}
          </p>
        </section>
      )}
    </>
  );
}

function StatTile({
  icon,
  tone,
  label,
  value,
  actionLabel,
  to,
}: {
  icon: React.ReactNode;
  tone: string;
  label: string;
  value: string;
  actionLabel: string;
  to: string;
}) {
  return (
    <div className="stat-card">
      <div className="stat-card__top">
        <span className={`icon-tile ${tone}`}>{icon}</span>
        <span className="stat-card__label">{label}</span>
      </div>
      <span className="stat-card__value">{value}</span>
      <Link to={to} className="stat-card__foot">
        {actionLabel} <ArrowRight size={15} />
      </Link>
    </div>
  );
}
