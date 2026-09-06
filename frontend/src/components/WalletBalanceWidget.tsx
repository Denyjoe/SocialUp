import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { fetchWallet } from "../api/endpoints/wallet";
import { useMoney } from "../currency/CurrencyContext";

export function WalletBalanceWidget() {
  const { t } = useTranslation();
  // The wallet is always denominated in the base currency, so the amount
  // needs no currency argument: the formatter converts for display only.
  const money = useMoney();
  const { data, isLoading } = useQuery({ queryKey: ["wallet"], queryFn: fetchWallet });

  return (
    <div className="wallet-widget" title={t("wallet.walletBalance")}>
      <span className="wallet-widget__label">{t("wallet.balance")}</span>
      <span className="wallet-widget__amount">
        {isLoading || !data ? "…" : money(data.cached_balance)}
      </span>
    </div>
  );
}
