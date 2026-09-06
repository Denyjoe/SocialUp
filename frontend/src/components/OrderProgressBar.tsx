import { useTranslation } from "react-i18next";

/** Statuses where a delivery percentage is meaningful. Completed already
 * reads as "100% done" from its badge alone, and refunded/canceled/error
 * orders never delivered anything worth graphing, so none of those get a
 * bar — only the ones still moving, plus partial (to show how far a
 * stalled delivery actually got). */
const BAR_STATUSES = new Set(["pending", "in_progress", "processing", "partial"]);

interface OrderProgressBarProps {
  status: string;
  progressPercent: number | null;
}

/** Live delivery progress bar, shown alongside (not instead of) the status
 * badge. `progressPercent` comes from the backend (Order.progress_percent)
 * so the dashboard, admin, and any future surface all agree on the exact
 * same number. `null` means the provider hasn't reported a remains count
 * yet — rendered as an indeterminate strip rather than a misleading 0%. */
export function OrderProgressBar({ status, progressPercent }: OrderProgressBarProps) {
  const { t } = useTranslation();

  if (!BAR_STATUSES.has(status)) return null;

  if (progressPercent === null) {
    return (
      <div className="order-progress order-progress--indeterminate" role="progressbar" aria-label={t("orders.progress.awaitingProvider")}>
        <div className="order-progress__track">
          <div className="order-progress__fill order-progress__fill--pulse" />
        </div>
        <span className="order-progress__label muted">{t("orders.progress.awaitingProvider")}</span>
      </div>
    );
  }

  return (
    <div
      className="order-progress"
      role="progressbar"
      aria-valuenow={progressPercent}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className="order-progress__track">
        <div className="order-progress__fill" style={{ width: `${progressPercent}%` }} />
      </div>
      <span className="order-progress__label">{t("orders.progress.delivered", { percent: progressPercent })}</span>
    </div>
  );
}
