import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { Bitcoin, CheckCircle2, Clock, ShieldCheck, X, XCircle } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { createDeposit, fetchDepositStatus, fetchDeposits } from "../../api/endpoints/payments";
import { DepositStatusBadge } from "../../components/DepositStatusBadge";
import { useCurrency, useMoney } from "../../currency/CurrencyContext";
import { PENDING_DEPOSIT_STATUSES, type DepositStatus } from "../../types/payments";
import { extractErrorMessage } from "../../utils/errors";

// Kept in sync by convention with MIN_DEPOSIT_USD in
// apps/payments/services.py — cheap enough to duplicate for a hint here
// rather than adding an endpoint just to expose one constant. The backend
// stays the authority: it rejects anything below this regardless of what
// this hint says.
const MIN_DEPOSIT_USD = 5;

const TERMINAL_ICON: Partial<Record<DepositStatus, "success" | "danger">> = {
  finished: "success",
  failed: "danger",
  expired: "danger",
};

export function AddFundsPage() {
  const { t } = useTranslation();
  const money = useMoney();
  const { rates, base } = useCurrency();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const [amount, setAmount] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);

  const returningReference = searchParams.get("deposit");
  const returningResult = searchParams.get("result");

  const usdRate = Number(rates.USD);
  const amountValue = Number(amount);
  const approxUsd = usdRate > 0 && amountValue > 0 ? amountValue * usdRate : null;
  const minimumLocal = usdRate > 0 ? MIN_DEPOSIT_USD / usdRate : null;

  const createMutation = useMutation({
    mutationFn: createDeposit,
    onSuccess: (txn) => {
      // Off to NOWPayments' hosted checkout page — a real navigation, not a
      // client-side route, so a full redirect is correct here.
      window.location.href = txn.checkout_url;
    },
    onError: (err) => setFieldError(extractErrorMessage(err, t("addFunds.couldNotStart"))),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setFieldError(null);
    if (!amountValue || amountValue <= 0) {
      setFieldError(t("addFunds.enterAnAmount"));
      return;
    }
    createMutation.mutate({ amount: amountValue });
  }

  const statusQuery = useQuery({
    queryKey: ["deposit-status", returningReference],
    queryFn: () => fetchDepositStatus(returningReference!),
    enabled: !!returningReference,
    retry: false,
    refetchInterval: (query) => {
      const txn = query.state.data;
      return txn && PENDING_DEPOSIT_STATUSES.includes(txn.status) ? 5000 : false;
    },
  });

  const settledStatus = statusQuery.data?.status;
  useEffect(() => {
    // A deposit that just left the "still moving" states may have credited
    // the wallet — refresh both instead of waiting for their own timers.
    if (settledStatus && !PENDING_DEPOSIT_STATUSES.includes(settledStatus)) {
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["deposits"] });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settledStatus]);

  function dismissStatus() {
    const next = new URLSearchParams(searchParams);
    next.delete("deposit");
    next.delete("result");
    setSearchParams(next, { replace: true });
  }

  const historyQuery = useQuery({ queryKey: ["deposits"], queryFn: fetchDeposits });
  const deposits = historyQuery.data ?? [];

  const tone = settledStatus ? TERMINAL_ICON[settledStatus] : undefined;

  return (
    <>
      <div className="page-header-row">
        <h1>{t("addFunds.title")}</h1>
      </div>
      <p className="page-subtitle">{t("addFunds.subtitle")}</p>

      {returningReference && (
        <section className="panel">
          <div className="panel-header">
            <span
              className={`icon-tile${tone ? ` icon-tile--${tone}` : " icon-tile--info"}`}
            >
              {tone === "success" ? (
                <CheckCircle2 size={18} />
              ) : tone === "danger" ? (
                <XCircle size={18} />
              ) : (
                <Clock size={18} />
              )}
            </span>
            <h2>{t("addFunds.statusPanelTitle")}</h2>
            <button
              type="button"
              className="btn-ghost btn-icon"
              onClick={dismissStatus}
              aria-label={t("common.close")}
              style={{ marginLeft: "auto" }}
            >
              <X size={16} />
            </button>
          </div>

          {statusQuery.isLoading && <p className="page-loading">{t("common.loading")}</p>}
          {statusQuery.isError && <p className="form-error">{t("addFunds.statusNotFound")}</p>}

          {statusQuery.data && (
            <>
              <p>
                <DepositStatusBadge status={statusQuery.data.status} />
              </p>
              <p>{t(`addFunds.statusBody.${statusQuery.data.status}`)}</p>
              {returningResult === "cancelled" && statusQuery.data.status === "waiting" && (
                <p className="form-hint">{t("addFunds.statusCancelledNote")}</p>
              )}
            </>
          )}
        </section>
      )}

      <div className="dashboard-columns">
        <section className="panel">
          <div className="panel-header">
            <span className="icon-tile">
              <Bitcoin size={18} />
            </span>
            <h2>{t("addFunds.depositPanelTitle")}</h2>
          </div>

          {fieldError && <p className="form-error">{fieldError}</p>}

          <form onSubmit={onSubmit} noValidate className="new-order-form">
            <label>
              {t("addFunds.amountLabel", { currency: base })}
              <input
                type="number"
                min={1}
                placeholder="50000"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
              <span className="field-hint">
                {approxUsd !== null
                  ? t("addFunds.approxUsd", { amount: approxUsd.toFixed(2) })
                  : minimumLocal !== null
                    ? t("addFunds.minimumHint", { amount: money(minimumLocal) })
                    : null}
              </span>
            </label>

            <button type="submit" className="btn-block" disabled={createMutation.isPending}>
              {createMutation.isPending ? t("addFunds.submitting") : t("addFunds.submit")}
            </button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-header">
            <span className="icon-tile icon-tile--info">
              <ShieldCheck size={18} />
            </span>
            <h2>{t("addFunds.howItWorksTitle")}</h2>
          </div>
          <ol className="how-to-list">
            <li>{t("addFunds.howTo1")}</li>
            <li>{t("addFunds.howTo2")}</li>
            <li>{t("addFunds.howTo3")}</li>
          </ol>
          <div className="how-to-note">
            <ShieldCheck size={15} />
            <span>{t("addFunds.securityNote")}</span>
          </div>
          <div className="how-to-note">
            <Clock size={15} />
            <span>{t("addFunds.localPaymentComingSoon")}</span>
          </div>
        </section>
      </div>

      <div className="page-header-row" style={{ marginTop: "2rem" }}>
        <h2>{t("addFunds.historyTitle")}</h2>
      </div>

      {historyQuery.isLoading && <p className="page-loading">{t("common.loading")}</p>}
      {historyQuery.isError && <p className="form-error">{t("addFunds.historyCouldNotLoad")}</p>}

      {!historyQuery.isLoading && deposits.length === 0 && (
        <div className="panel">
          <div className="empty-state">
            <span className="empty-state__icon">
              <Bitcoin size={22} />
            </span>
            <h3>{t("addFunds.noDeposits")}</h3>
            <p>{t("addFunds.noDepositsBody")}</p>
          </div>
        </div>
      )}

      {deposits.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("addFunds.column.amount")}</th>
                <th>{t("addFunds.column.method")}</th>
                <th>{t("common.status")}</th>
                <th>{t("addFunds.column.date")}</th>
              </tr>
            </thead>
            <tbody>
              {deposits.map((txn) => (
                <tr key={txn.id}>
                  <td>
                    <strong>{money(txn.amount_local)}</strong>
                  </td>
                  <td>{txn.gateway_label}</td>
                  <td>
                    <DepositStatusBadge status={txn.status} />
                  </td>
                  <td className="muted nowrap">{new Date(txn.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
