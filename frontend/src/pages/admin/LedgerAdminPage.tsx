import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchAdminLedger } from "../../api/endpoints/admin/wallet";
import { Pagination } from "../../components/Pagination";
import { formatMoney } from "../../utils/format";

const ENTRY_TYPE_LABELS: Record<string, string> = {
  deposit: "Deposit",
  order_payment: "Order payment",
  order_refund: "Order refund",
  admin_credit: "Admin credit",
  admin_debit: "Admin debit",
  affiliate_commission: "Affiliate commission",
};

export function LedgerAdminPage() {
  const [page, setPage] = useState(1);
  const [userSearch, setUserSearch] = useState("");
  const [entryType, setEntryType] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "ledger", page, userSearch, entryType],
    queryFn: () =>
      fetchAdminLedger({ page, user: userSearch || undefined, entry_type: entryType || undefined }),
  });

  return (
    <div className="admin-ledger-page">
      <div className="page-header-row">
        <h1>Wallet ledger</h1>
      </div>
      <p className="muted">Every credit and debit across every wallet. Entries are immutable, so this is a complete audit trail.</p>

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
          value={entryType}
          onChange={(e) => {
            setEntryType(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All types</option>
          {Object.entries(ENTRY_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {isLoading && <p>Loading ledger…</p>}
      {data && (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Type</th>
                  <th>Amount</th>
                  <th>Balance after</th>
                  <th>Description</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((entry) => (
                  <tr key={entry.id}>
                    <td>{entry.user_email}</td>
                    <td>{ENTRY_TYPE_LABELS[entry.entry_type] ?? entry.entry_type}</td>
                    <td className={Number(entry.amount) >= 0 ? "amount-positive" : "amount-negative"}>
                      {Number(entry.amount) >= 0 ? "+" : ""}
                      {formatMoney(entry.amount)}
                    </td>
                    <td>{formatMoney(entry.balance_after)}</td>
                    <td>{entry.description}</td>
                    <td>{new Date(entry.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} count={data.count} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}
