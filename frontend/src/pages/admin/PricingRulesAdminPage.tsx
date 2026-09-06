import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Percent, Plus, RefreshCcw, Trash2, X } from "lucide-react";

import {
  createPricingRule,
  deletePricingRule,
  fetchAdminCategories,
  fetchPricingRules,
  repriceFromRules,
  updatePricingRule,
  type PricingRuleInput,
} from "../../api/endpoints/admin/catalog";
import { useConfirm } from "../../components/ConfirmDialogProvider";
import type { AdminPricingRule } from "../../types/admin";
import { extractErrorMessage } from "../../utils/errors";

/** Must match apps.catalog.models.Category.Platform on the backend. */
const PLATFORMS = [
  { value: "instagram", label: "Instagram" },
  { value: "tiktok", label: "TikTok" },
  { value: "youtube", label: "YouTube" },
  { value: "facebook", label: "Facebook" },
  { value: "twitter", label: "Twitter / X" },
  { value: "telegram", label: "Telegram" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "spotify", label: "Spotify" },
  { value: "other", label: "Other" },
];

const SCOPE_LABELS: Record<AdminPricingRule["scope"], string> = {
  category: "Category",
  platform: "Platform",
  cost_tier: "Cost range",
};

function platformLabel(value: string) {
  return PLATFORMS.find((p) => p.value === value)?.label ?? value;
}

function ruleTarget(rule: AdminPricingRule): string {
  if (rule.scope === "category") return rule.category_name ?? "Not set";
  if (rule.scope === "platform") return platformLabel(rule.platform);
  const min = rule.min_cost_per_1000 ? `$${rule.min_cost_per_1000}` : "$0";
  const max = rule.max_cost_per_1000 ? `$${rule.max_cost_per_1000}` : "no limit";
  return `${min} – ${max}`;
}

export function PricingRulesAdminPage() {
  const queryClient = useQueryClient();
  const confirmDialog = useConfirm();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<AdminPricingRule | null>(null);
  const [repriceResult, setRepriceResult] = useState<string | null>(null);

  const { data: categories } = useQuery({
    queryKey: ["admin", "categories"],
    queryFn: fetchAdminCategories,
  });
  const { data: rules, isLoading } = useQuery({
    queryKey: ["admin", "pricing-rules"],
    queryFn: fetchPricingRules,
  });

  const remove = useMutation({
    mutationFn: deletePricingRule,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "pricing-rules"] }),
  });

  const reprice = useMutation({
    mutationFn: repriceFromRules,
    onSuccess: (res) => {
      setRepriceResult(res.detail);
      queryClient.invalidateQueries({ queryKey: ["admin", "services"] });
    },
  });

  function openEdit(rule: AdminPricingRule) {
    setEditing(rule);
    setShowForm(true);
  }

  function openCreate() {
    setEditing(null);
    setShowForm(true);
  }

  return (
    <>
      <div className="page-header-row">
        <h1>Pricing rules</h1>
        <div className="page-header-actions">
          <button
            className="btn-secondary btn-sm"
            disabled={reprice.isPending}
            onClick={async () => {
              if (
                await confirmDialog({
                  title: "Reprice from rules",
                  message:
                    "Re-evaluate every active, unlocked, non-overridden service against the rules below? Services with their own manual price are never touched.",
                  confirmLabel: "Reprice",
                })
              ) {
                setRepriceResult(null);
                reprice.mutate();
              }
            }}
          >
            <RefreshCcw size={14} />
            {reprice.isPending ? "Repricing…" : "Reprice from rules"}
          </button>
          <button className="btn-sm" onClick={openCreate}>
            <Plus size={14} /> New rule
          </button>
        </div>
      </div>
      <p className="page-subtitle">
        These apply automatically every time the catalogue syncs, so a new service picks up whichever
        rule matches it, with no manual pricing needed. A service with its own manual price (set in
        Services &amp; Pricing) always overrides every rule below. When more than one rule matches,
        the highest priority wins.
      </p>
      {repriceResult && <p className="form-success">{repriceResult}</p>}

      {showForm && (
        <RuleForm
          rule={editing}
          categories={categories ?? []}
          onClose={() => setShowForm(false)}
        />
      )}

      {isLoading && <p className="page-loading">Loading pricing rules…</p>}
      {rules && rules.length === 0 && (
        <p className="muted">
          No rules yet. Every service falls back to the single default markup in Settings. Add a
          rule to price a category, platform, or cost range differently.
        </p>
      )}
      {rules && rules.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Scope</th>
                <th>Target</th>
                <th>Markup</th>
                <th>Min profit</th>
                <th>Priority</th>
                <th>Matches now</th>
                <th>Active</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id} className="clickable-row" onClick={() => openEdit(rule)}>
                  <td>{rule.name}</td>
                  <td>{SCOPE_LABELS[rule.scope]}</td>
                  <td>{ruleTarget(rule)}</td>
                  <td>{rule.markup_percent}%</td>
                  <td>{rule.min_profit_per_1000 ?? "Not set"}</td>
                  <td>{rule.priority}</td>
                  <td>{rule.matching_services_count.toLocaleString()}</td>
                  <td>
                    <span
                      className={`status-badge ${rule.is_active ? "status-badge--completed" : "status-badge--pending"}`}
                    >
                      {rule.is_active ? "Active" : "Off"}
                    </span>
                  </td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      className="btn-ghost btn-icon"
                      aria-label={`Delete ${rule.name}`}
                      onClick={async () => {
                        if (
                          await confirmDialog({
                            title: "Delete rule",
                            message: `Delete "${rule.name}"? Services keep their current price.`,
                            confirmLabel: "Delete",
                            danger: true,
                          })
                        ) {
                          remove.mutate(rule.id);
                        }
                      }}
                    >
                      <Trash2 size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function RuleForm({
  rule,
  categories,
  onClose,
}: {
  rule: AdminPricingRule | null;
  categories: { id: number; name: string }[];
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const isEdit = !!rule;

  const [name, setName] = useState(rule?.name ?? "");
  const [scope, setScope] = useState<AdminPricingRule["scope"]>(rule?.scope ?? "category");
  const [category, setCategory] = useState(rule?.category ? String(rule.category) : "");
  const [platform, setPlatform] = useState(rule?.platform ?? "instagram");
  const [minCost, setMinCost] = useState(rule?.min_cost_per_1000 ?? "");
  const [maxCost, setMaxCost] = useState(rule?.max_cost_per_1000 ?? "");
  const [markup, setMarkup] = useState(rule?.markup_percent ?? "40.00");
  const [minProfit, setMinProfit] = useState(rule?.min_profit_per_1000 ?? "");
  const [priority, setPriority] = useState(String(rule?.priority ?? 0));
  const [isActive, setIsActive] = useState(rule?.is_active ?? true);
  const [error, setError] = useState<string | null>(null);

  function buildPayload(): PricingRuleInput {
    return {
      name,
      scope,
      category: scope === "category" ? Number(category) : null,
      platform: scope === "platform" ? platform : "",
      min_cost_per_1000: scope === "cost_tier" && minCost ? minCost : null,
      max_cost_per_1000: scope === "cost_tier" && maxCost ? maxCost : null,
      markup_percent: markup,
      min_profit_per_1000: minProfit || null,
      priority: Number(priority),
      is_active: isActive,
    };
  }

  const save = useMutation({
    mutationFn: () => (isEdit ? updatePricingRule(rule!.id, buildPayload()) : createPricingRule(buildPayload())),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "pricing-rules"] });
      onClose();
    },
    onError: (err) => setError(extractErrorMessage(err, "Could not save this rule.")),
  });

  return (
    <section className="panel">
      <div className="panel-header">
        <span className="icon-tile icon-tile--warning">
          <Percent size={18} />
        </span>
        <h2>{isEdit ? "Edit rule" : "New pricing rule"}</h2>
        <button className="btn-ghost btn-icon" onClick={onClose} aria-label="Close">
          <X size={16} />
        </button>
      </div>

      {error && <p className="form-error">{error}</p>}

      <form
        className="modal-form"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <label>
          Name
          <input
            type="text"
            required
            placeholder="e.g. Cheap services need a higher %"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>

        <label>
          Applies to
          <select value={scope} onChange={(e) => setScope(e.target.value as AdminPricingRule["scope"])}>
            <option value="category">A specific category</option>
            <option value="platform">A whole platform</option>
            <option value="cost_tier">A cost range (USD per 1000)</option>
          </select>
        </label>

        {scope === "category" && (
          <label>
            Category
            <select value={category} onChange={(e) => setCategory(e.target.value)} required>
              <option value="" disabled>
                Choose a category…
              </option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
        )}

        {scope === "platform" && (
          <label>
            Platform
            <select value={platform} onChange={(e) => setPlatform(e.target.value)}>
              {PLATFORMS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
        )}

        {scope === "cost_tier" && (
          <div className="row" style={{ gap: "0.75rem" }}>
            <label style={{ flex: 1 }}>
              Min cost (USD, optional)
              <input
                type="number"
                step="0.0001"
                min="0"
                placeholder="0"
                value={minCost}
                onChange={(e) => setMinCost(e.target.value)}
              />
            </label>
            <label style={{ flex: 1 }}>
              Max cost (USD, optional)
              <input
                type="number"
                step="0.0001"
                min="0"
                placeholder="No limit"
                value={maxCost}
                onChange={(e) => setMaxCost(e.target.value)}
              />
            </label>
          </div>
        )}

        <label>
          Markup (%)
          <input
            type="number"
            step="0.01"
            min="0"
            required
            value={markup}
            onChange={(e) => setMarkup(e.target.value)}
          />
        </label>

        <label>
          Minimum profit per 1000 (optional)
          <input
            type="number"
            step="0.01"
            min="0"
            placeholder="Leave blank for none"
            value={minProfit}
            onChange={(e) => setMinProfit(e.target.value)}
          />
          <span className="field-hint">
            In your local currency. Guarantees at least this much profit even when the % above
            rounds to almost nothing on a very cheap service.
          </span>
        </label>

        <label>
          Priority
          <input
            type="number"
            step="1"
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
          />
          <span className="field-hint">Higher runs first when a service matches more than one rule.</span>
        </label>

        <label className="checkbox-label">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          Active
        </label>

        <button type="submit" disabled={save.isPending}>
          {save.isPending ? "Saving…" : isEdit ? "Save changes" : "Create rule"}
        </button>
      </form>
    </section>
  );
}
