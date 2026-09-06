import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { addTicketMessage, createTicket, fetchTicketDetail, fetchTickets } from "../../api/endpoints/support";
import { Modal } from "../../components/Modal";
import type { TicketCategory } from "../../types/support";
import { extractErrorMessage } from "../../utils/errors";

const CATEGORY_KEYS: Record<TicketCategory, string> = {
  general: "support.category.general",
  billing: "support.category.billing",
  order_issue: "support.category.orderIssue",
  technical: "support.category.technical",
  other: "support.category.other",
};

export function TicketsPage() {
  const { t } = useTranslation();
  const [showNewForm, setShowNewForm] = useState(false);
  const [openTicketId, setOpenTicketId] = useState<number | null>(null);
  const { data: tickets, isLoading } = useQuery({ queryKey: ["tickets"], queryFn: fetchTickets });

  return (
    <div className="tickets-page">
      <div className="page-header-row">
        <h1>{t("support.title")}</h1>
        <button onClick={() => setShowNewForm(true)}>{t("support.newTicket")}</button>
      </div>

      {isLoading && <p>{t("support.loadingTickets")}</p>}
      {tickets && tickets.length === 0 && <p className="muted">{t("support.noTickets")}</p>}
      {tickets && tickets.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("support.subject")}</th>
                <th>{t("support.category")}</th>
                <th>{t("common.status")}</th>
                <th>{t("support.messages")}</th>
                <th>{t("support.updated")}</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((ticket) => (
                <tr
                  key={ticket.id}
                  className="clickable-row"
                  onClick={() => setOpenTicketId(ticket.id)}
                >
                  <td>{ticket.subject}</td>
                  <td>{t(CATEGORY_KEYS[ticket.category])}</td>
                  <td>
                    <span className={`status-pill ticket-status--${ticket.status}`}>
                      {t(`support.status.${ticket.status}`)}
                    </span>
                  </td>
                  <td>{ticket.message_count}</td>
                  <td>{new Date(ticket.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showNewForm && <NewTicketModal onClose={() => setShowNewForm(false)} />}
      {openTicketId && <TicketThreadModal ticketId={openTicketId} onClose={() => setOpenTicketId(null)} />}
    </div>
  );
}

function NewTicketModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState<TicketCategory>("general");
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => createTicket({ subject, category, message }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tickets"] });
      onClose();
    },
    onError: (err) => setError(extractErrorMessage(err, t("support.couldNotCreate"))),
  });

  return (
    <Modal title={t("support.newTicket")} onClose={onClose}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          mutation.mutate();
        }}
        className="modal-form"
      >
        {error && <p className="form-error">{error}</p>}
        <label>
          {t("support.subject")}
          <input type="text" required value={subject} onChange={(e) => setSubject(e.target.value)} />
        </label>
        <label>
          {t("support.category")}
          <select value={category} onChange={(e) => setCategory(e.target.value as TicketCategory)}>
            {Object.entries(CATEGORY_KEYS).map(([value, labelKey]) => (
              <option key={value} value={value}>
                {t(labelKey)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("support.message")}
          <textarea required rows={4} value={message} onChange={(e) => setMessage(e.target.value)} />
        </label>
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? t("common.submitting") : t("support.submit")}
        </button>
      </form>
    </Modal>
  );
}

function TicketThreadModal({ ticketId, onClose }: { ticketId: number; onClose: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [reply, setReply] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: ticket, isLoading } = useQuery({
    queryKey: ["ticket", ticketId],
    queryFn: () => fetchTicketDetail(ticketId),
  });

  const mutation = useMutation({
    mutationFn: () => addTicketMessage(ticketId, reply),
    onSuccess: () => {
      setReply("");
      queryClient.invalidateQueries({ queryKey: ["ticket", ticketId] });
      queryClient.invalidateQueries({ queryKey: ["tickets"] });
    },
    onError: (err) => setError(extractErrorMessage(err, t("support.couldNotReply"))),
  });

  return (
    <Modal title={ticket ? ticket.subject : t("support.ticket")} onClose={onClose}>
      {isLoading || !ticket ? (
        <p>{t("common.loading")}</p>
      ) : (
        <div className="ticket-thread">
          <div className="ticket-thread__messages">
            {ticket.messages.map((m) => (
              <div key={m.id} className={`ticket-message ${m.is_staff_reply ? "ticket-message--staff" : ""}`}>
                <div className="ticket-message__meta">
                  <strong>{m.is_staff_reply ? t("support.staffReply") : t("support.you")}</strong>
                  <span className="muted">{new Date(m.created_at).toLocaleString()}</span>
                </div>
                <p>{m.body}</p>
              </div>
            ))}
          </div>
          {ticket.status !== "closed" ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setError(null);
                mutation.mutate();
              }}
              className="ticket-reply-form"
            >
              {error && <p className="form-error">{error}</p>}
              <textarea
                required
                rows={3}
                placeholder={t("support.writeReply")}
                value={reply}
                onChange={(e) => setReply(e.target.value)}
              />
              <button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? t("common.sending") : t("common.send")}
              </button>
            </form>
          ) : (
            <p className="muted">{t("support.closedNotice")}</p>
          )}
        </div>
      )}
    </Modal>
  );
}
