import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Gift, Plus, Tags, Trash2 } from "lucide-react";

import {
  createCoupon,
  createDepositBonus,
  deleteCoupon,
  deleteDepositBonus,
  fetchCoupons,
  fetchDepositBonuses,
  updateCoupon,
  updateDepositBonus,
} from "../../api/endpoints/admin/promotions";
import { useConfirm } from "../../components/ConfirmDialogProvider";
import { Modal } from "../../components/Modal";
import { extractErrorMessage } from "../../utils/errors";
import { formatMoney } from "../../utils/format";

export function CouponsAdminPage() {
  const [tab, setTab] = useState<"coupons" | "bonuses">("coupons");

  return (
    <>
      <div className="page-header-row">
        <h1>Coupons and bonuses</h1>
      </div>
      <p className="page-subtitle">
        Discount codes apply to orders. Deposit bonuses add extra balance when a customer tops up.
      </p>

      <div className="segmented">
        <button
          type="button"
          className={tab === "coupons" ? "active" : ""}
          onClick={() => setTab("coupons")}
        >
          Discount codes
        </button>
        <button
          type="button"
          className={tab === "bonuses" ? "active" : ""}
          onClick={() => setTab("bonuses")}
        >
          Deposit bonuses
        </button>
      </div>

      {tab === "coupons" ? <CouponsPanel /> : <BonusesPanel />}
    </>
  );
}

function CouponsPanel() {
  const queryClient = useQueryClient();
  const confirmDialog = useConfirm();
  const [showForm, setShowForm] = useState(false);
  const { data, isLoading } = useQuery({ queryKey: ["admin-coupons"], queryFn: fetchCoupons });

  const toggle = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      updateCoupon(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-coupons"] }),
  });

  const remove = useMutation({
    mutationFn: deleteCoupon,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-coupons"] }),
  });

  const coupons = data?.results ?? [];

  return (
    <section className="panel">
      <div className="panel-header">
        <span className="icon-tile">
          <Tags size={18} />
        </span>
        <h2>Discount codes</h2>
        <button className="btn-sm" style={{ marginLeft: "auto" }} onClick={() => setShowForm(true)}>
          <Plus size={15} /> New code
        </button>
      </div>

      {isLoading && <p className="page-loading">Loading…</p>}

      {!isLoading && coupons.length === 0 && (
        <div className="empty-state">
          <span className="empty-state__icon">
            <Tags size={22} />
          </span>
          <h3>No discount codes yet</h3>
          <p>Create a code and customers can apply it at checkout.</p>
        </div>
      )}

      {coupons.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Discount</th>
                <th>Min order</th>
                <th>Used</th>
                <th>Expires</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {coupons.map((c) => (
                <tr key={c.id}>
                  <td>
                    <strong>{c.code}</strong>
                    {c.description && <div className="text-sm muted">{c.description}</div>}
                  </td>
                  <td>
                    {c.discount_type === "percent"
                      ? `${Number(c.value)}%`
                      : formatMoney(c.value)}
                    {c.max_discount_amount && (
                      <div className="text-sm muted">
                        Capped at {formatMoney(c.max_discount_amount)}
                      </div>
                    )}
                  </td>
                  <td className="muted">
                    {Number(c.min_order_amount) > 0 ? formatMoney(c.min_order_amount) : "Any"}
                  </td>
                  <td>
                    {c.used_count}
                    {c.max_uses !== null && ` of ${c.max_uses}`}
                  </td>
                  <td className="muted nowrap">
                    {c.expires_at ? new Date(c.expires_at).toLocaleDateString() : "No expiry"}
                  </td>
                  <td>
                    <span
                      className={`status-badge ${
                        c.is_active ? "status-badge--completed" : "status-badge--refunded"
                      }`}
                    >
                      {c.is_active ? "Active" : "Paused"}
                    </span>
                  </td>
                  <td>
                    <div className="admin-row-actions">
                      <button
                        className="btn-secondary btn-sm"
                        onClick={() => toggle.mutate({ id: c.id, is_active: !c.is_active })}
                      >
                        {c.is_active ? "Pause" : "Activate"}
                      </button>
                      <button
                        className="btn-ghost btn-icon"
                        aria-label={`Delete ${c.code}`}
                        onClick={async () => {
                          if (
                            await confirmDialog({
                              title: "Delete coupon",
                              message: `Delete coupon ${c.code}? This cannot be undone.`,
                              confirmLabel: "Delete",
                              danger: true,
                            })
                          ) {
                            remove.mutate(c.id);
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

      {showForm && <CouponForm onClose={() => setShowForm(false)} />}
    </section>
  );
}

function CouponForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [discountType, setDiscountType] = useState("percent");
  const [value, setValue] = useState("");
  const [minOrder, setMinOrder] = useState("");
  const [maxDiscount, setMaxDiscount] = useState("");
  const [maxUses, setMaxUses] = useState("");
  const [maxPerUser, setMaxPerUser] = useState("1");
  const [expiresAt, setExpiresAt] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: createCoupon,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-coupons"] });
      onClose();
    },
    onError: (err) => setError(extractErrorMessage(err, "Could not create the coupon.")),
  });

  return (
    <Modal title="New discount code" onClose={onClose}>
      <form
        className="modal-form"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          create.mutate({
            code,
            description,
            discount_type: discountType,
            value,
            min_order_amount: minOrder || "0",
            max_discount_amount: maxDiscount || null,
            max_uses: maxUses ? Number(maxUses) : null,
            max_uses_per_user: Number(maxPerUser) || 1,
            expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
          });
        }}
      >
        {error && <p className="form-error">{error}</p>}
        <label>
          Code
          <input
            required
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="WELCOME10"
          />
        </label>
        <label>
          Description
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Shown to you only, not to customers"
          />
        </label>
        <label>
          Discount type
          <select value={discountType} onChange={(e) => setDiscountType(e.target.value)}>
            <option value="percent">Percent off</option>
            <option value="fixed">Fixed amount off</option>
          </select>
        </label>
        <label>
          {discountType === "percent" ? "Percent off" : "Amount off in TZS"}
          <input
            required
            type="number"
            step="0.01"
            min="0"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
        </label>
        {discountType === "percent" && (
          <label>
            Maximum discount in TZS
            <input
              type="number"
              step="0.01"
              min="0"
              value={maxDiscount}
              onChange={(e) => setMaxDiscount(e.target.value)}
              placeholder="Leave blank for no cap"
            />
          </label>
        )}
        <label>
          Minimum order in TZS
          <input
            type="number"
            step="0.01"
            min="0"
            value={minOrder}
            onChange={(e) => setMinOrder(e.target.value)}
            placeholder="0"
          />
        </label>
        <label>
          Total uses allowed
          <input
            type="number"
            min="1"
            value={maxUses}
            onChange={(e) => setMaxUses(e.target.value)}
            placeholder="Leave blank for unlimited"
          />
        </label>
        <label>
          Uses per customer
          <input
            type="number"
            min="1"
            value={maxPerUser}
            onChange={(e) => setMaxPerUser(e.target.value)}
          />
        </label>
        <label>
          Expires on
          <input type="date" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} />
        </label>
        <button type="submit" disabled={create.isPending}>
          {create.isPending ? "Creating…" : "Create code"}
        </button>
      </form>
    </Modal>
  );
}

function BonusesPanel() {
  const queryClient = useQueryClient();
  const confirmDialog = useConfirm();
  const [showForm, setShowForm] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["admin-deposit-bonuses"],
    queryFn: fetchDepositBonuses,
  });

  const toggle = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      updateDepositBonus(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-deposit-bonuses"] }),
  });

  const remove = useMutation({
    mutationFn: deleteDepositBonus,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-deposit-bonuses"] }),
  });

  const rules = data?.results ?? [];

  return (
    <section className="panel">
      <div className="panel-header">
        <span className="icon-tile icon-tile--success">
          <Gift size={18} />
        </span>
        <h2>Deposit bonuses</h2>
        <button className="btn-sm" style={{ marginLeft: "auto" }} onClick={() => setShowForm(true)}>
          <Plus size={15} /> New rule
        </button>
      </div>

      <p className="field-hint" style={{ marginBottom: "1rem" }}>
        When a customer tops up, the highest matching rule applies. These take effect once mobile
        money deposits go live, and already apply to balances you add manually.
      </p>

      {isLoading && <p className="page-loading">Loading…</p>}

      {!isLoading && rules.length === 0 && (
        <div className="empty-state">
          <span className="empty-state__icon">
            <Gift size={22} />
          </span>
          <h3>No bonus rules yet</h3>
          <p>Reward bigger top ups with extra balance.</p>
        </div>
      )}

      {rules.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Applies from</th>
                <th>Bonus</th>
                <th>Cap</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id}>
                  <td>
                    <strong>{rule.name}</strong>
                  </td>
                  <td>{formatMoney(rule.min_amount)}</td>
                  <td>{Number(rule.bonus_percent)}%</td>
                  <td className="muted">
                    {rule.max_bonus_amount ? formatMoney(rule.max_bonus_amount) : "No cap"}
                  </td>
                  <td>
                    <span
                      className={`status-badge ${
                        rule.is_active ? "status-badge--completed" : "status-badge--refunded"
                      }`}
                    >
                      {rule.is_active ? "Active" : "Paused"}
                    </span>
                  </td>
                  <td>
                    <div className="admin-row-actions">
                      <button
                        className="btn-secondary btn-sm"
                        onClick={() => toggle.mutate({ id: rule.id, is_active: !rule.is_active })}
                      >
                        {rule.is_active ? "Pause" : "Activate"}
                      </button>
                      <button
                        className="btn-ghost btn-icon"
                        aria-label={`Delete ${rule.name}`}
                        onClick={async () => {
                          if (
                            await confirmDialog({
                              title: "Delete bonus rule",
                              message: `Delete bonus rule "${rule.name}"?`,
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
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && <BonusForm onClose={() => setShowForm(false)} />}
    </section>
  );
}

function BonusForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [minAmount, setMinAmount] = useState("");
  const [percent, setPercent] = useState("");
  const [cap, setCap] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: createDepositBonus,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-deposit-bonuses"] });
      onClose();
    },
    onError: (err) => setError(extractErrorMessage(err, "Could not create the rule.")),
  });

  return (
    <Modal title="New deposit bonus" onClose={onClose}>
      <form
        className="modal-form"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          create.mutate({
            name,
            min_amount: minAmount,
            bonus_percent: percent,
            max_bonus_amount: cap || null,
          });
        }}
      >
        {error && <p className="form-error">{error}</p>}
        <label>
          Name
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Big top up bonus"
          />
        </label>
        <label>
          Applies from, in TZS
          <input
            required
            type="number"
            step="0.01"
            min="0"
            value={minAmount}
            onChange={(e) => setMinAmount(e.target.value)}
            placeholder="50000"
          />
        </label>
        <label>
          Bonus percent
          <input
            required
            type="number"
            step="0.01"
            min="0"
            value={percent}
            onChange={(e) => setPercent(e.target.value)}
            placeholder="10"
          />
        </label>
        <label>
          Maximum bonus in TZS
          <input
            type="number"
            step="0.01"
            min="0"
            value={cap}
            onChange={(e) => setCap(e.target.value)}
            placeholder="Leave blank for no cap"
          />
        </label>
        <button type="submit" disabled={create.isPending}>
          {create.isPending ? "Creating…" : "Create rule"}
        </button>
      </form>
    </Modal>
  );
}
