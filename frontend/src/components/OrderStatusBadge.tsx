import { useTranslation } from "react-i18next";

import type { OrderStatus } from "../types/api";

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  const { t } = useTranslation();
  return (
    <span className={`status-badge status-badge--${status}`}>
      {t(`orders.status.${status}`, status)}
    </span>
  );
}
