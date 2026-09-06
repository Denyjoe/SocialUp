import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef, useState, type FormEvent } from "react";
import { CheckCircle2, HelpCircle, Link2, PlusCircle, ShoppingCart, X, XCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { bulkCreateOrders, type BulkOrderResult } from "../../api/endpoints/orders";
import { ServicePicker } from "../../components/ServicePicker";
import { useMoney } from "../../currency/CurrencyContext";
import type { Service } from "../../types/api";
import { extractErrorMessage } from "../../utils/errors";

interface Row {
  id: number;
  service: Service | null;
  link: string;
  quantity: string;
}

let nextRowId = 1;
function emptyRow(): Row {
  return { id: nextRowId++, service: null, link: "", quantity: "" };
}

// Matches the backend's MAX_BULK_LINES (apps/orders/views.py) — kept in
// sync by convention, not a shared constant, since one is Python and the
// other TypeScript. If that number ever changes, change it here too.
const MAX_ROWS = 25;

export function BulkOrderPage() {
  const { t } = useTranslation();
  const money = useMoney();
  const queryClient = useQueryClient();

  const [rows, setRows] = useState<Row[]>([emptyRow(), emptyRow()]);
  const [resultsByRowId, setResultsByRowId] = useState<Map<number, BulkOrderResult>>(new Map());
  const [summary, setSummary] = useState<{ placed: number; failed: number } | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const submittedIds = useRef<number[]>([]);

  const mutation = useMutation({
    mutationFn: bulkCreateOrders,
    onSuccess: (results) => {
      setServerError(null);
      setFieldError(null);
      const ids = submittedIds.current;
      const map = new Map(ids.map((id, i) => [id, results[i]]));
      setResultsByRowId(map);
      setSummary({
        placed: results.filter((r) => r.success).length,
        failed: results.filter((r) => !r.success).length,
      });
      setRows((prev) => {
        const remaining = prev.filter((row) => !map.get(row.id)?.success);
        return remaining.length > 0 ? remaining : [emptyRow()];
      });
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
    onError: (err) => setServerError(extractErrorMessage(err, t("bulkOrder.couldNotSubmit"))),
  });

  const total = useMemo(() => {
    return rows.reduce((sum, row) => {
      const qty = Number(row.quantity);
      if (!row.service || !qty || qty <= 0) return sum;
      return sum + (Number(row.service.retail_rate_per_1000) * qty) / 1000;
    }, 0);
  }, [rows]);

  function updateRow(id: number, patch: Partial<Row>) {
    setRows((prev) => prev.map((row) => (row.id === id ? { ...row, ...patch } : row)));
  }

  function addRow() {
    if (rows.length >= MAX_ROWS) return;
    setRows((prev) => [...prev, emptyRow()]);
  }

  function removeRow(id: number) {
    setRows((prev) => (prev.length > 1 ? prev.filter((row) => row.id !== id) : prev));
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setFieldError(null);
    setSummary(null);

    // Only structural completeness is checked here — a bad quantity range
    // or an inactive service is a per-line business rule, and the backend
    // already reports that clearly against the specific row, exactly the
    // same messages a single New Order would show.
    const incomplete = rows.some(
      (row) => !row.service || !row.link.trim() || !Number(row.quantity) || Number(row.quantity) <= 0
    );
    if (incomplete) return setFieldError(t("bulkOrder.completeEveryRow"));

    submittedIds.current = rows.map((row) => row.id);
    mutation.mutate(
      rows.map((row) => ({
        service: row.service!.id,
        link: row.link.trim(),
        quantity: Number(row.quantity),
      }))
    );
  }

  return (
    <>
      <div className="page-header-row">
        <h1>{t("bulkOrder.title")}</h1>
      </div>
      <p className="page-subtitle">{t("bulkOrder.subtitle")}</p>

      <div className="dashboard-columns">
        <section className="panel">
          <div className="panel-header">
            <span className="icon-tile">
              <ShoppingCart size={18} />
            </span>
            <h2>{t("bulkOrder.placeOrders")}</h2>
          </div>

          {serverError && <p className="form-error">{serverError}</p>}
          {fieldError && <p className="form-error">{fieldError}</p>}
          {summary && (
            <p className={summary.failed === 0 ? "form-success" : "form-hint"}>
              {summary.failed === 0 ? (
                <CheckCircle2 size={15} style={{ verticalAlign: "-2px" }} />
              ) : (
                <XCircle size={15} style={{ verticalAlign: "-2px" }} />
              )}{" "}
              {t("bulkOrder.summary", { placed: summary.placed, failed: summary.failed })}
              {summary.placed > 0 && (
                <>
                  {" "}
                  <Link to="/dashboard/orders">{t("newOrder.viewHistory")}</Link>
                </>
              )}
            </p>
          )}

          <form onSubmit={onSubmit} noValidate>
            {rows.map((row, index) => {
              const result = resultsByRowId.get(row.id);
              return (
                <div className="bulk-order-row" key={row.id}>
                  <div className="bulk-order-row__header">
                    <span className="bulk-order-row__title">
                      {t("bulkOrder.orderNumber", { number: index + 1 })}
                    </span>
                    {rows.length > 1 && (
                      <button
                        type="button"
                        className="btn-ghost btn-icon"
                        onClick={() => removeRow(row.id)}
                        aria-label={t("bulkOrder.removeRow")}
                      >
                        <X size={16} />
                      </button>
                    )}
                  </div>

                  <div className="new-order-form">
                    <label>
                      {t("newOrder.service")}
                      <ServicePicker value={row.service} onChange={(service) => updateRow(row.id, { service })} />
                    </label>

                    <label>
                      {t("newOrder.link")}
                      <input
                        type="url"
                        placeholder="https://instagram.com/yourprofile"
                        value={row.link}
                        onChange={(e) => updateRow(row.id, { link: e.target.value })}
                      />
                    </label>

                    <label>
                      {t("newOrder.quantity")}
                      <input
                        type="number"
                        min={1}
                        placeholder="1000"
                        value={row.quantity}
                        onChange={(e) => updateRow(row.id, { quantity: e.target.value })}
                      />
                      {row.service && (
                        <span className="field-hint">
                          {t("newOrder.quantityRange", {
                            min: row.service.min_quantity.toLocaleString(),
                            max: row.service.max_quantity.toLocaleString(),
                          })}
                        </span>
                      )}
                    </label>
                  </div>

                  {result && (
                    <p className={result.success ? "form-success" : "form-error"}>
                      {result.success ? (
                        <>
                          <CheckCircle2 size={15} style={{ verticalAlign: "-2px" }} /> {t("bulkOrder.rowSuccess")}
                        </>
                      ) : (
                        <>
                          <XCircle size={15} style={{ verticalAlign: "-2px" }} /> {result.error}
                        </>
                      )}
                    </p>
                  )}
                </div>
              );
            })}

            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={addRow}
              disabled={rows.length >= MAX_ROWS}
              style={{ marginBottom: "1rem" }}
            >
              <PlusCircle size={15} /> {t("bulkOrder.addAnother")}
            </button>

            {total > 0 && (
              <div className="price-estimate">
                <span>{t("bulkOrder.estimatedTotal")}</span>
                <strong>{money(total)}</strong>
              </div>
            )}

            <button type="submit" className="btn-block" disabled={mutation.isPending}>
              {mutation.isPending
                ? t("bulkOrder.placing")
                : t("bulkOrder.placeAll", { count: rows.length })}
            </button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-header">
            <span className="icon-tile icon-tile--info">
              <HelpCircle size={18} />
            </span>
            <h2>{t("bulkOrder.howTo")}</h2>
          </div>
          <ol className="how-to-list">
            <li>{t("bulkOrder.howTo1")}</li>
            <li>{t("bulkOrder.howTo2")}</li>
            <li>{t("bulkOrder.howTo3")}</li>
          </ol>
          <div className="how-to-note">
            <Link2 size={15} />
            <span>{t("bulkOrder.limitNote", { max: MAX_ROWS })}</span>
          </div>
        </section>
      </div>
    </>
  );
}
