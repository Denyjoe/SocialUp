import { useTranslation } from "react-i18next";

import type { DepositStatus } from "../types/payments";

// Deposits have their own status vocabulary (NOWPayments' invoice
// lifecycle), but reuse the order status badge's colour language rather
// than inventing a parallel set of CSS classes.
const STYLE: Record<DepositStatus, string> = {
  waiting: "pending",
  confirming: "processing",
  confirmed: "in_progress",
  sending: "in_progress",
  partially_paid: "partial",
  finished: "completed",
  failed: "error",
  expired: "canceled",
};

export function DepositStatusBadge({ status }: { status: DepositStatus }) {
  const { t } = useTranslation();
  return (
    <span className={`status-badge status-badge--${STYLE[status]}`}>
      {t(`addFunds.status.${status}`, status)}
    </span>
  );
}
