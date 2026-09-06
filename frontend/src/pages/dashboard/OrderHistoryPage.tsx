import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, PlusCircle, ShoppingBag } from "lucide-react";
import { useTranslation } from "react-i18next";

import { fetchOrders } from "../../api/endpoints/orders";
import { OrderProgressBar } from "../../components/OrderProgressBar";
import { OrderStatusBadge } from "../../components/OrderStatusBadge";
import { useMoney } from "../../currency/CurrencyContext";
import type { OrderStatus } from "../../types/api";

const FILTERS: { value: string; label: string }[] = [
  { value: "", label: "common.all" },
  { value: "pending", label: "orders.status.pending" },
  { value: "in_progress", label: "orders.status.in_progress" },
  { value: "completed", label: "orders.status.completed" },
  { value: "refunded", label: "orders.status.refunded" },
];

export function OrderHistoryPage() {
  const { t } = useTranslation();
  const money = useMoney();
  const [filter, setFilter] = useState("");

  const { data: orders, isLoading, isError } = useQuery({
    queryKey: ["orders"],
    queryFn: fetchOrders,
    // Cheap way to reflect provider status updates without websockets.
    refetchInterval: 10_000,
  });

  const visible = (orders ?? []).filter((o) => !filter || o.status === (filter as OrderStatus));

  return (
    <>
      <div className="page-header-row">
        <h1>{t("orders.title")}</h1>
        <div className="page-header-actions">
          <Link to="/dashboard/new-order" className="btn btn-sm">
            <PlusCircle size={15} /> {t("nav.newOrder")}
          </Link>
        </div>
      </div>
      <p className="page-subtitle">{t("orders.subtitle")}</p>

      <div className="segmented">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            className={filter === f.value ? "active" : ""}
            onClick={() => setFilter(f.value)}
          >
            {t(f.label)}
          </button>
        ))}
      </div>

      {isLoading && <p className="page-loading">{t("common.loading")}</p>}
      {isError && <p className="form-error">{t("orders.couldNotLoad")}</p>}

      {!isLoading && visible.length === 0 && (
        <div className="panel">
          <div className="empty-state">
            <span className="empty-state__icon">
              <ShoppingBag size={22} />
            </span>
            <h3>{filter ? t("orders.nothingHere") : t("orders.none")}</h3>
            <p>
              {filter
                ? t("orders.noMatch")
                : t("orders.noneBody")}
            </p>
            {!filter && (
              <Link to="/dashboard/new-order" className="btn">
                {t("orders.placeAnOrder")}
              </Link>
            )}
          </div>
        </div>
      )}

      {visible.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("orders.service")}</th>
                <th>{t("orders.link")}</th>
                <th>{t("orders.quantity")}</th>
                <th>{t("orders.charged")}</th>
                <th>{t("common.status")}</th>
                <th>{t("orders.placed")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((order) => (
                <tr key={order.id}>
                  <td>{order.service_name}</td>
                  <td>
                    <a
                      href={order.link}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="row"
                      style={{ gap: "0.3rem" }}
                    >
                      {t("orders.open")} <ExternalLink size={13} />
                    </a>
                  </td>
                  <td>{order.quantity.toLocaleString()}</td>
                  <td>
                    <strong>{money(order.charge_amount)}</strong>
                    {Number(order.discount_amount) > 0 && (
                      <div className="text-sm amount-positive">
                        {t("orders.saved", { amount: money(order.discount_amount) })}
                      </div>
                    )}
                  </td>
                  <td>
                    <OrderStatusBadge status={order.status} />
                    <OrderProgressBar status={order.status} progressPercent={order.progress_percent} />
                  </td>
                  <td className="muted nowrap">{new Date(order.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
