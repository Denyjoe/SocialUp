import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  fetchAdminTicketDetail,
  fetchAdminTickets,
  replyToTicket,
  setTicketStatus,
} from "../../api/endpoints/admin/tickets";
import { Modal } from "../../components/Modal";
import { Pagination } from "../../components/Pagination";
import type { TicketStatus } from "../../types/support";
import { extractErrorMessage } from "../../utils/errors";

const STATUS_OPTIONS: TicketStatus[] = ["open", "answered", "pending", "closed"];

export function TicketsAdminPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [userSearch, setUserSearch] = useState("");
  const [openTicketId, setOpenTicketId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "tickets", page, statusFilter, userSearch],
    queryFn: () => fetchAdminTickets({ page, status: statusFilter || undefined, user: userSearch || undefined }),
  });

  return (
    <div className="admin-tickets-page">
      <div className="page-header-row">
        <h1>Support tickets</h1>
      </div>
      <p className="page-subtitle">Customer questions and issues.</p>

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

      {isLoading && <p>Loading tickets…</p>}
      {data && (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Subject</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((t) => (
                  <tr key={t.id} className="clickable-row" onClick={() => setOpenTicketId(t.id)}>
                    <td>{t.user_email}</td>
                    <td>{t.subject}</td>
                    <td>{t.category}</td>
                    <td>
                      <span className={`status-pill ticket-status--${t.status}`}>{t.status}</span>
                    </td>
                    <td>{t.priority}</td>
                    <td>{new Date(t.updated_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} count={data.count} onPageChange={setPage} />
        </>
      )}

      {openTicketId && <AdminTicketModal ticketId={openTicketId} onClose={() => setOpenTicketId(null)} />}
    </div>
  );
}

function AdminTicketModal({ ticketId, onClose }: { ticketId: number; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [reply, setReply] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: ticket, isLoading } = useQuery({
    queryKey: ["admin", "ticket", ticketId],
    queryFn: () => fetchAdminTicketDetail(ticketId),
  });

  const replyMutation = useMutation({
    mutationFn: () => replyToTicket(ticketId, reply),
    onSuccess: () => {
      setReply("");
      queryClient.invalidateQueries({ queryKey: ["admin", "ticket", ticketId] });
      queryClient.invalidateQueries({ queryKey: ["admin", "tickets"] });
    },
    onError: (err) => setError(extractErrorMessage(err, "Could not send the reply.")),
  });

  const statusMutation = useMutation({
    mutationFn: (status: TicketStatus) => setTicketStatus(ticketId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "ticket", ticketId] });
      queryClient.invalidateQueries({ queryKey: ["admin", "tickets"] });
    },
  });

  return (
    <Modal title={ticket ? `${ticket.subject} (${ticket.user_email})` : "Ticket"} onClose={onClose}>
      {isLoading || !ticket ? (
        <p>Loading…</p>
      ) : (
        <div className="ticket-thread">
          <div className="admin-row-actions" style={{ marginBottom: "0.75rem" }}>
            {STATUS_OPTIONS.map((s) => (
              <button
                key={s}
                disabled={ticket.status === s || statusMutation.isPending}
                onClick={() => statusMutation.mutate(s)}
              >
                Mark {s}
              </button>
            ))}
          </div>
          <div className="ticket-thread__messages">
            {ticket.messages.map((m) => (
              <div key={m.id} className={`ticket-message ${m.is_staff_reply ? "ticket-message--staff" : ""}`}>
                <div className="ticket-message__meta">
                  <strong>{m.is_staff_reply ? "Support (you)" : ticket.user_email}</strong>
                  <span className="muted">{new Date(m.created_at).toLocaleString()}</span>
                </div>
                <p>{m.body}</p>
              </div>
            ))}
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setError(null);
              replyMutation.mutate();
            }}
            className="ticket-reply-form"
          >
            {error && <p className="form-error">{error}</p>}
            <textarea
              required
              rows={3}
              placeholder="Write a reply…"
              value={reply}
              onChange={(e) => setReply(e.target.value)}
            />
            <button type="submit" disabled={replyMutation.isPending}>
              {replyMutation.isPending ? "Sending…" : "Reply"}
            </button>
          </form>
        </div>
      )}
    </Modal>
  );
}
