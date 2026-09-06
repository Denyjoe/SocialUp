import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { adjustUserBalance, fetchAdminUsers, setUserStatus } from "../../api/endpoints/admin/users";
import { Modal } from "../../components/Modal";
import { Pagination } from "../../components/Pagination";
import type { AdminUser } from "../../types/admin";
import { extractErrorMessage } from "../../utils/errors";
import { formatMoney } from "../../utils/format";

export function UsersAdminPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [balanceTarget, setBalanceTarget] = useState<AdminUser | null>(null);

  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "users", page, search, statusFilter],
    queryFn: () => fetchAdminUsers({ page, search: search || undefined, status: statusFilter || undefined }),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: "active" | "suspended" | "banned" }) =>
      setUserStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "users"] }),
  });

  return (
    <div className="admin-users-page">
      <div className="page-header-row">
        <h1>Users</h1>
      </div>
      <p className="page-subtitle">Search customers, adjust balances, and suspend or ban accounts.</p>

      <div className="admin-filters">
        <input
          type="search"
          placeholder="Search by email…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
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
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="banned">Banned</option>
        </select>
      </div>

      {isLoading && <p>Loading users…</p>}
      {data && (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Status</th>
                  <th>Balance</th>
                  <th>Orders</th>
                  <th>Joined</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((u) => (
                  <tr key={u.id}>
                    <td>{u.email}</td>
                    <td>
                      <span className={`status-pill status-pill--${u.status}`}>{u.status}</span>
                    </td>
                    <td>{formatMoney(u.wallet_balance, u.wallet_currency)}</td>
                    <td>{u.orders_count}</td>
                    <td>{new Date(u.date_joined).toLocaleDateString()}</td>
                    <td className="admin-row-actions">
                      <button onClick={() => setBalanceTarget(u)}>Adjust balance</button>
                      {u.status !== "suspended" && (
                        <button onClick={() => statusMutation.mutate({ id: u.id, status: "suspended" })}>
                          Suspend
                        </button>
                      )}
                      {u.status !== "active" && (
                        <button onClick={() => statusMutation.mutate({ id: u.id, status: "active" })}>
                          Reactivate
                        </button>
                      )}
                      {u.status !== "banned" && (
                        <button
                          className="danger"
                          onClick={() => statusMutation.mutate({ id: u.id, status: "banned" })}
                        >
                          Ban
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

      {balanceTarget && (
        <AdjustBalanceModal
          user={balanceTarget}
          onClose={() => setBalanceTarget(null)}
          onDone={() => {
            setBalanceTarget(null);
            queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
          }}
        />
      )}
    </div>
  );
}

function AdjustBalanceModal({
  user,
  onClose,
  onDone,
}: {
  user: AdminUser;
  onClose: () => void;
  onDone: () => void;
}) {
  const [direction, setDirection] = useState<"credit" | "debit">("credit");
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => adjustUserBalance(user.id, { direction, amount, reason }),
    onSuccess: onDone,
    onError: (err) => setError(extractErrorMessage(err, "Could not adjust the balance.")),
  });

  return (
    <Modal title={`Adjust balance for ${user.email}`} onClose={onClose}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          mutation.mutate();
        }}
        className="modal-form"
      >
        <p className="muted">Current balance: {formatMoney(user.wallet_balance, user.wallet_currency)}</p>
        {error && <p className="form-error">{error}</p>}
        <label>
          Direction
          <select value={direction} onChange={(e) => setDirection(e.target.value as "credit" | "debit")}>
            <option value="credit">Credit (add funds)</option>
            <option value="debit">Debit (remove funds)</option>
          </select>
        </label>
        <label>
          Amount ({user.wallet_currency})
          <input
            type="number"
            min="0.01"
            step="0.01"
            required
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </label>
        <label>
          Reason (optional)
          <input type="text" value={reason} onChange={(e) => setReason(e.target.value)} />
        </label>
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Apply"}
        </button>
      </form>
    </Modal>
  );
}
