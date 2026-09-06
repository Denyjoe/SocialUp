import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  fetchAdminProviders,
  fetchProviderSyncLogs,
  triggerProviderBalanceCheck,
  triggerProviderSync,
  updateAdminProvider,
} from "../../api/endpoints/admin/providers";
import { Modal } from "../../components/Modal";
import type { AdminProvider } from "../../types/admin";
import { extractErrorMessage } from "../../utils/errors";
import { formatMoney } from "../../utils/format";

export function ProvidersAdminPage() {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<AdminProvider | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const { data: providers, isLoading } = useQuery({
    queryKey: ["admin", "providers"],
    queryFn: fetchAdminProviders,
  });
  const { data: logs } = useQuery({
    queryKey: ["admin", "sync-logs"],
    queryFn: () => fetchProviderSyncLogs(),
  });

  const syncMutation = useMutation({
    mutationFn: triggerProviderSync,
    onSuccess: () => {
      setToast("Service sync started. This can take a while for a large catalogue, so refresh in a moment.");
      queryClient.invalidateQueries({ queryKey: ["admin", "sync-logs"] });
    },
  });
  const balanceMutation = useMutation({
    mutationFn: triggerProviderBalanceCheck,
    onSuccess: () => {
      setToast("Balance check queued.");
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ["admin", "providers"] }), 1500);
    },
  });

  return (
    <div className="admin-providers-page">
      <div className="page-header-row">
        <h1>Providers</h1>
      </div>
      <p className="page-subtitle">Upstream suppliers that fulfil your orders.</p>
      {toast && <p className="form-success">{toast}</p>}

      {isLoading && <p>Loading providers…</p>}
      {providers && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Services</th>
                <th>Balance</th>
                <th>Checked</th>
                <th>Active</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((p) => (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td>{p.provider_type}</td>
                  <td>{p.services_count.toLocaleString()}</td>
                  <td>{formatMoney(p.balance_cached, p.balance_currency)}</td>
                  <td>{p.balance_last_checked_at ? new Date(p.balance_last_checked_at).toLocaleString() : "Never"}</td>
                  <td>{p.is_active ? "Yes" : "No"}</td>
                  <td className="admin-row-actions">
                    <button onClick={() => setEditing(p)}>Edit</button>
                    <button onClick={() => balanceMutation.mutate(p.id)} disabled={balanceMutation.isPending}>
                      Check balance
                    </button>
                    <button onClick={() => syncMutation.mutate(p.id)} disabled={syncMutation.isPending}>
                      Sync services
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <section className="panel">
        <h2>Recent sync activity</h2>
        {!logs || logs.length === 0 ? (
          <p className="muted">No syncs run yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Updated</th>
                  <th>Started</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td>{log.provider_name}</td>
                    <td>
                      <span className={`status-pill status-pill--${log.status === "success" ? "active" : "banned"}`}>
                        {log.status}
                      </span>
                    </td>
                    <td>{log.services_created}</td>
                    <td>{log.services_updated}</td>
                    <td>{new Date(log.started_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {editing && <EditProviderModal provider={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function EditProviderModal({ provider, onClose }: { provider: AdminProvider; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [baseUrl, setBaseUrl] = useState(provider.base_url);
  const [apiKey, setApiKey] = useState("");
  const [isActive, setIsActive] = useState(provider.is_active);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      updateAdminProvider(provider.id, {
        base_url: baseUrl,
        is_active: isActive,
        ...(apiKey ? { api_key: apiKey } : {}),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "providers"] });
      onClose();
    },
    onError: (err) => setError(extractErrorMessage(err, "Could not update the provider.")),
  });

  return (
    <Modal title={`Edit provider: ${provider.name}`} onClose={onClose}>
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
          Base URL
          <input type="url" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
        </label>
        <label>
          API key
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={provider.has_api_key ? "Leave blank to keep the current key" : "No key set"}
          />
        </label>
        <label className="checkbox-label">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Active
        </label>
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Save"}
        </button>
      </form>
    </Modal>
  );
}
