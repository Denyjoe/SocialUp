import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Mail, Megaphone, Plus, Trash2 } from "lucide-react";

import {
  createAnnouncement,
  deleteAnnouncement,
  fetchAdminAnnouncements,
  sendAnnouncementEmail,
  updateAnnouncement,
} from "../../api/endpoints/admin/announcements";
import { useConfirm } from "../../components/ConfirmDialogProvider";
import { Modal } from "../../components/Modal";
import { extractErrorMessage } from "../../utils/errors";

export function AnnouncementsAdminPage() {
  const queryClient = useQueryClient();
  const confirmDialog = useConfirm();
  const [showForm, setShowForm] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-announcements"],
    queryFn: fetchAdminAnnouncements,
  });

  const toggle = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      updateAnnouncement(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-announcements"] }),
  });

  const remove = useMutation({
    mutationFn: deleteAnnouncement,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-announcements"] }),
  });

  const sendEmail = useMutation({
    mutationFn: sendAnnouncementEmail,
    onSuccess: (res) => {
      setToast(res.detail);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["admin-announcements"] });
    },
    onError: (err) => setError(extractErrorMessage(err, "Could not send the email.")),
  });

  const rows = data?.results ?? [];

  return (
    <>
      <div className="page-header-row">
        <h1>Announcements</h1>
        <div className="page-header-actions">
          <button className="btn-sm" onClick={() => setShowForm(true)}>
            <Plus size={15} /> New announcement
          </button>
        </div>
      </div>
      <p className="page-subtitle">
        Live announcements show as a banner on every customer dashboard. Emailing is a separate
        action, so editing a banner never mails anyone by accident.
      </p>

      {toast && <p className="form-success">{toast}</p>}
      {error && <p className="form-error">{error}</p>}

      <section className="panel">
        {isLoading && <p className="page-loading">Loading…</p>}

        {!isLoading && rows.length === 0 && (
          <div className="empty-state">
            <span className="empty-state__icon">
              <Megaphone size={22} />
            </span>
            <h3>No announcements yet</h3>
            <p>Post downtime notices, price changes or promotions.</p>
          </div>
        )}

        {rows.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Level</th>
                  <th>Showing</th>
                  <th>Emailed</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <strong>{a.title}</strong>
                      <div className="text-sm muted">{a.body.slice(0, 90)}</div>
                    </td>
                    <td>
                      <span
                        className={`status-badge ${
                          a.level === "warning"
                            ? "status-badge--pending"
                            : a.level === "success"
                              ? "status-badge--completed"
                              : "status-badge--in_progress"
                        }`}
                      >
                        {a.level}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`status-badge ${
                          a.is_live ? "status-badge--completed" : "status-badge--refunded"
                        }`}
                      >
                        {a.is_live ? "Live" : "Hidden"}
                      </span>
                    </td>
                    <td className="muted nowrap">
                      {a.emailed_at
                        ? `${a.email_recipient_count} sent`
                        : "Not sent"}
                    </td>
                    <td>
                      <div className="admin-row-actions">
                        <button
                          className="btn-secondary btn-sm"
                          onClick={() => toggle.mutate({ id: a.id, is_active: !a.is_active })}
                        >
                          {a.is_active ? "Hide" : "Show"}
                        </button>
                        <button
                          className="btn-secondary btn-sm"
                          disabled={!!a.emailed_at || sendEmail.isPending}
                          onClick={async () => {
                            if (
                              await confirmDialog({
                                title: "Email all customers",
                                message: `Email "${a.title}" to every active customer? This cannot be undone.`,
                                confirmLabel: "Send",
                                danger: true,
                              })
                            ) {
                              sendEmail.mutate(a.id);
                            }
                          }}
                        >
                          <Mail size={14} /> {a.emailed_at ? "Sent" : "Email all"}
                        </button>
                        <button
                          className="btn-ghost btn-icon"
                          aria-label={`Delete ${a.title}`}
                          onClick={async () => {
                            if (
                              await confirmDialog({
                                title: "Delete announcement",
                                message: `Delete "${a.title}"?`,
                                confirmLabel: "Delete",
                                danger: true,
                              })
                            ) {
                              remove.mutate(a.id);
                            }
                          }}
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {showForm && <AnnouncementForm onClose={() => setShowForm(false)} />}
    </>
  );
}

function AnnouncementForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [level, setLevel] = useState("info");
  const [dismissible, setDismissible] = useState(true);
  const [endsAt, setEndsAt] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: createAnnouncement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-announcements"] });
      onClose();
    },
    onError: (err) => setError(extractErrorMessage(err, "Could not create the announcement.")),
  });

  return (
    <Modal title="New announcement" onClose={onClose}>
      <form
        className="modal-form"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          create.mutate({
            title,
            body,
            level,
            is_active: true,
            dismissible,
            ends_at: endsAt ? new Date(endsAt).toISOString() : null,
          });
        }}
      >
        {error && <p className="form-error">{error}</p>}
        <label>
          Title
          <input
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Scheduled maintenance on Sunday"
          />
        </label>
        <label>
          Message
          <textarea
            required
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Keep it short. This shows in a banner."
          />
        </label>
        <label>
          Level
          <select value={level} onChange={(e) => setLevel(e.target.value)}>
            <option value="info">Info, blue</option>
            <option value="success">Success, green</option>
            <option value="warning">Warning, amber</option>
          </select>
        </label>
        <label>
          Stop showing on
          <input type="date" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} />
          <span className="field-hint">Leave blank to show until you hide it.</span>
        </label>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={dismissible}
            onChange={(e) => setDismissible(e.target.checked)}
          />
          Customers can dismiss this banner
        </label>
        <button type="submit" disabled={create.isPending}>
          {create.isPending ? "Creating…" : "Create announcement"}
        </button>
      </form>
    </Modal>
  );
}
