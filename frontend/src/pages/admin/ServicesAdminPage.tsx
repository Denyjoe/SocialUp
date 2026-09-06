import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { SlidersHorizontal, X } from "lucide-react";

import {
  bulkUpdateServices,
  fetchAdminCategories,
  fetchAdminServices,
  updateAdminService,
} from "../../api/endpoints/admin/catalog";
import { useConfirm } from "../../components/ConfirmDialogProvider";
import { Pagination } from "../../components/Pagination";
import type { AdminService } from "../../types/admin";
import { extractErrorMessage } from "../../utils/errors";
import { formatMoney } from "../../utils/format";

export function ServicesAdminPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [activeOnly, setActiveOnly] = useState(false);
  const [showBulk, setShowBulk] = useState(false);

  const { data: categories } = useQuery({
    queryKey: ["admin", "categories"],
    queryFn: fetchAdminCategories,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "services", page, search, category, activeOnly],
    queryFn: () =>
      fetchAdminServices({
        page,
        search: search || undefined,
        category: category ? Number(category) : undefined,
        is_active: activeOnly ? true : undefined,
      }),
  });

  return (
    <>
      <div className="page-header-row">
        <h1>Services and pricing</h1>
        <div className="page-header-actions">
          <button className="btn-secondary btn-sm" onClick={() => setShowBulk(true)}>
            <SlidersHorizontal size={15} /> Bulk update
          </button>
        </div>
      </div>
      <p className="page-subtitle">
        {data ? `${data.count.toLocaleString()} services` : "…"} across your provider catalogue.
        Retail is what customers pay per 1000, priced automatically from provider cost unless the
        service is locked.
      </p>

      {showBulk && (
        <BulkUpdatePanel categories={categories ?? []} onClose={() => setShowBulk(false)} />
      )}

      <div className="admin-filters">
        <input
          type="search"
          placeholder="Search by service name…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
        <select
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All categories</option>
          {categories?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} ({c.services_count})
            </option>
          ))}
        </select>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={(e) => {
              setActiveOnly(e.target.checked);
              setPage(1);
            }}
          />
          Active only
        </label>
      </div>

      {isLoading && <p className="page-loading">Loading services…</p>}
      {data && (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Category</th>
                  <th>Cost per 1000</th>
                  <th>Retail per 1000</th>
                  <th>Margin</th>
                  <th>Locked</th>
                  <th>Active</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((service) => (
                  <ServiceRow key={service.id} service={service} />
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} count={data.count} onPageChange={setPage} />
        </>
      )}
    </>
  );
}

function BulkUpdatePanel({
  categories,
  onClose,
}: {
  categories: { id: number; name: string; services_count: number }[];
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const confirmDialog = useConfirm();
  const [category, setCategory] = useState("");
  const [action, setAction] = useState("adjust_price");
  const [value, setValue] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = useMutation({
    mutationFn: bulkUpdateServices,
    onSuccess: (res) => {
      setResult(res.detail);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["admin", "services"] });
    },
    onError: (err) => setError(extractErrorMessage(err, "Bulk update failed.")),
  });

  const needsValue = action === "adjust_price" || action === "set_markup";
  const target = category
    ? categories.find((c) => String(c.id) === category)?.name
    : "every category";

  return (
    <section className="panel">
      <div className="panel-header">
        <span className="icon-tile icon-tile--warning">
          <SlidersHorizontal size={18} />
        </span>
        <h2>Bulk update</h2>
        <button className="btn-ghost btn-icon" onClick={onClose} aria-label="Close">
          <X size={16} />
        </button>
      </div>

      {result && <p className="form-success">{result}</p>}
      {error && <p className="form-error">{error}</p>}

      <div className="admin-filters">
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} ({c.services_count})
            </option>
          ))}
        </select>
        <select value={action} onChange={(e) => setAction(e.target.value)}>
          <option value="adjust_price">Adjust retail price by percent</option>
          <option value="set_markup">Set markup and reprice from cost</option>
          <option value="activate">Activate</option>
          <option value="deactivate">Deactivate</option>
        </select>
        {needsValue && (
          <input
            type="number"
            step="0.01"
            placeholder={action === "adjust_price" ? "e.g. 10 or -5" : "e.g. 40"}
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
        )}
        <button
          disabled={run.isPending}
          onClick={async () => {
            const label =
              action === "adjust_price"
                ? `adjust prices by ${value}%`
                : action === "set_markup"
                  ? `set markup to ${value}%`
                  : action;
            if (
              await confirmDialog({
                title: "Bulk update",
                message: `Apply "${label}" to ${target}? This affects many services at once.`,
                confirmLabel: "Apply",
              })
            ) {
              run.mutate({
                category: category ? Number(category) : undefined,
                action,
                value: needsValue ? Number(value) : undefined,
              });
            }
          }}
        >
          {run.isPending ? "Applying…" : "Apply"}
        </button>
      </div>

      <p className="field-hint">
        Price changes skip any service marked as locked. Activate and deactivate apply to all
        matching services.
      </p>
    </section>
  );
}

function ServiceRow({ service }: { service: AdminService }) {
  const queryClient = useQueryClient();
  const [price, setPrice] = useState(service.retail_rate_per_1000);

  const mutation = useMutation({
    mutationFn: (payload: Partial<AdminService>) => updateAdminService(service.id, payload),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "services"] });
      setPrice(updated.retail_rate_per_1000);
    },
  });

  return (
    <tr>
      <td>{service.name}</td>
      <td>{service.category_name}</td>
      <td>{formatMoney(service.cost_rate_per_1000, service.cost_currency)}</td>
      <td>
        <input
          type="number"
          step="0.01"
          value={price}
          disabled={mutation.isPending}
          onChange={(e) => setPrice(e.target.value)}
          onBlur={() => {
            if (price !== service.retail_rate_per_1000) {
              mutation.mutate({ retail_rate_per_1000: price, price_locked: true });
            }
          }}
          className="price-input"
        />
      </td>
      <td>{service.margin_percent !== null ? `${service.margin_percent}%` : "Not set"}</td>
      <td>
        <input
          type="checkbox"
          checked={service.price_locked}
          onChange={(e) => mutation.mutate({ price_locked: e.target.checked })}
        />
      </td>
      <td>
        <input
          type="checkbox"
          checked={service.is_active}
          onChange={(e) => mutation.mutate({ is_active: e.target.checked })}
        />
      </td>
    </tr>
  );
}
