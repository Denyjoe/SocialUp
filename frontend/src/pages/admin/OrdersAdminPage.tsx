import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  bulkOrderAction,
  fetchAdminOrderDetail,
  fetchAdminOrders,
  refundAdminOrder,
  retrySubmitAdminOrder,
} from "../../api/endpoints/admin/orders";
import { useConfirm } from "../../components/ConfirmDialogProvider";
import { Modal } from "../../components/Modal";
import { OrderProgressBar } from "../../components/OrderProgressBar";
import { OrderStatusBadge } from "../../components/OrderStatusBadge";
import { Pagination } from "../../components/Pagination";
import type { OrderStatus } from "../../types/api";
import { extractErrorMessage } from "../../utils/errors";
import { formatMoney } from "../../utils/format";

const STATUS_OPTIONS: OrderStatus[] = [
  "pending",
  "in_progress",
  "processing",
  "completed",
  "partial",
  "canceled",
  "refunded",
  "error",
];

export function OrdersAdminPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [userSearch, setUserSearch] = useState("");
  const [detailId, setDetailId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [bulkResult, setBulkResult] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const confirmDialog = useConfirm();

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "orders", page, statusFilter, userSearch],
    queryFn: () =>
      fetchAdminOrders({ page, status: statusFilter || undefined, user: userSearch || undefined }),
  });

  const refundMutation = useMutation({
    mutationFn: (id: string) => refundAdminOrder(id),
    onSuccess: () => {
      setActionError(null);
      queryClient.invalidateQueries({ queryKey: ["admin", "orders"] });
    },
    onError: (err) => setActionError(extractErrorMessage(err, "Could not refund this order.")),
  });
  const retryMutation = useMutation({
    mutationFn: (id: string) => retrySubmitAdminOrder(id),
    onSuccess: () => {
      setActionError(null);
      queryClient.invalidateQueries({ queryKey: ["admin", "orders"] });
    },
    onError: (err) => setActionError(extractErrorMessage(err, "Could not retry submission.")),
  });

  const bulk = useMutation({
    mutationFn: bulkOrderAction,
    onSuccess: (res) => {
      setActionError(null);
      setBulkResult(res.detail);
      setSelected([]);
      queryClient.invalidateQueries({ queryKey: ["admin", "orders"] });
    },
    onError: (err) => setActionError(extractErrorMessage(err, "Bulk action failed.")),
  });

  const pageIds = (data?.results ?? []).map((o) => o.id);
  const allSelected = pageIds.length > 0 && pageIds.every((id) => selected.includes(id));

  function toggleAll() {
    setSelected(allSelected ? [] : pageIds);
  }

  function toggleOne(id: string) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  return (
    <>
      <div className="page-header-row">
        <h1>Orders</h1>
      </div>
      {actionError && <p className="form-error">{actionError}</p>}
      {bulkResult && <p className="form-success">{bulkResult}</p>}

      {selected.length > 0 && (
        <div className="bulk-bar">
          <span>
            <strong>{selected.length}</strong> selected
          </span>
          <div className="row">
            <button
              className="btn-secondary btn-sm"
              disabled={bulk.isPending}
              onClick={async () => {
                if (
                  await confirmDialog({
                    title: "Refund orders",
                    message: `Refund ${selected.length} orders? Customers get their money back.`,
                    confirmLabel: "Refund",
                    danger: true,
                  })
                ) {
                  bulk.mutate({ order_ids: selected, action: "refund" });
                }
              }}
            >
              Refund selected
            </button>
            <button
              className="btn-secondary btn-sm"
              disabled={bulk.isPending}
              onClick={() => bulk.mutate({ order_ids: selected, action: "retry" })}
            >
              Retry submit
            </button>
            <button className="btn-ghost btn-sm" onClick={() => setSelected([])}>
              Clear
            </button>
          </div>
        </div>
      )}

      <div className="admin-filters">
        <input
          type="search"
          placeholder="Search by user email…"
          value={userSearch}
          onChange={(e) => {
            setUserSearch(e.target.value);
            setPage(1);
          }}
        />
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {isLoading && <p className="page-loading">Loading orders…</p>}
      {data && (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ width: "2.5rem" }}>
                    <input
                      type="checkbox"
                      checked={allSelected}
                      onChange={toggleAll}
                      aria-label="Select all on this page"
                    />
                  </th>
                  <th>User</th>
                  <th>Service</th>
                  <th>Quantity</th>
                  <th>Charged</th>
                  <th>Status</th>
                  <th>Placed</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((order) => (
                  <tr key={order.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selected.includes(order.id)}
                        onChange={() => toggleOne(order.id)}
                        aria-label={`Select order ${order.id}`}
                      />
                    </td>
                    <td>{order.user_email}</td>
                    <td>{order.service_name}</td>
                    <td>{order.quantity.toLocaleString()}</td>
                    <td>{formatMoney(order.charge_amount)}</td>
                    <td>
                      <OrderStatusBadge status={order.status as OrderStatus} />
                      <OrderProgressBar status={order.status} progressPercent={order.progress_percent} />
                    </td>
                    <td>{new Date(order.created_at).toLocaleString()}</td>
                    <td className="admin-row-actions">
                      <button className="btn-secondary btn-sm" onClick={() => setDetailId(order.id)}>
                        Details
                      </button>
                      {order.status !== "refunded" && (
                        <button
                          className="btn-secondary btn-sm"
                          onClick={() => refundMutation.mutate(order.id)}
                          disabled={refundMutation.isPending}
                        >
                          Refund
                        </button>
                      )}
                      {!order.provider_order_id && (
                        <button
                          className="btn-secondary btn-sm"
                          onClick={() => retryMutation.mutate(order.id)}
                          disabled={retryMutation.isPending}
                        >
                          Retry submit
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} count={data.count} onPageChange={setPage} />
        </>
      )}

      {detailId && <OrderDetailModal orderId={detailId} onClose={() => setDetailId(null)} />}
    </>
  );
}

function OrderDetailModal({ orderId, onClose }: { orderId: string; onClose: () => void }) {
  const { data: order, isLoading } = useQuery({
    queryKey: ["admin", "order-detail", orderId],
    queryFn: () => fetchAdminOrderDetail(orderId),
  });

  return (
    <Modal title="Order detail" onClose={onClose}>
      {isLoading || !order ? (
        <p>Loading…</p>
      ) : (
        <div className="order-detail">
          <dl>
            <dt>User</dt>
            <dd>{order.user_email}</dd>
            <dt>Service</dt>
            <dd>{order.service_name}</dd>
            <dt>Provider</dt>
            <dd>
              {order.provider_name} ({order.provider_order_id || "no provider order id"})
            </dd>
            <dt>Link</dt>
            <dd className="truncate">{order.link}</dd>
            <dt>Quantity</dt>
            <dd>{order.quantity.toLocaleString()}</dd>
            <dt>Charge</dt>
            <dd>{formatMoney(order.charge_amount)}</dd>
            <dt>Status</dt>
            <dd>
              <OrderStatusBadge status={order.status as OrderStatus} />
              <OrderProgressBar status={order.status} progressPercent={order.progress_percent} />
            </dd>
            {order.error_message && (
              <>
                <dt>Error</dt>
                <dd className="form-error">{order.error_message}</dd>
              </>
            )}
          </dl>
          <h4>Status history</h4>
          {order.status_history.length === 0 ? (
            <p className="muted">No history recorded.</p>
          ) : (
            <ul className="status-history">
              {order.status_history.map((entry, i) => (
                <li key={i}>
                  <strong>{entry.old_status || "New"}</strong> → <strong>{entry.new_status}</strong>{" "}
                  <span className="muted">
                    ({entry.source}, {new Date(entry.changed_at).toLocaleString()})
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Modal>
  );
}
