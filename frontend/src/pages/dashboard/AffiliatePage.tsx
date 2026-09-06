import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Check, Copy, Percent, Share2, Users, Wallet } from "lucide-react";

import { fetchAffiliateSummary, fetchReferrals } from "../../api/endpoints/affiliate";
import { useMoney } from "../../currency/CurrencyContext";
import { useTranslation } from "react-i18next";

export function AffiliatePage() {
  const { t } = useTranslation();
  const money = useMoney();
  const [copied, setCopied] = useState(false);
  const { data: summary, isLoading } = useQuery({
    queryKey: ["affiliate-summary"],
    queryFn: fetchAffiliateSummary,
  });
  const { data: referrals } = useQuery({
    queryKey: ["affiliate-referrals"],
    queryFn: fetchReferrals,
  });

  const referralLink = summary
    ? `${window.location.origin}/register?ref=${summary.referral_code}`
    : "";

  function copyLink() {
    navigator.clipboard.writeText(referralLink).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  if (isLoading || !summary) return <p className="page-loading">{t("common.loading")}</p>;

  return (
    <>
      <div className="page-header-row">
        <h1>{t("affiliate.title")}</h1>
      </div>
      <p className="page-subtitle">
        {t("affiliate.subtitle", { percent: summary.commission_percent })}
      </p>

      <div className="stat-grid stat-grid--3">
        <div className="stat-card">
          <div className="stat-card__top">
            <span className="icon-tile">
              <Percent size={18} />
            </span>
            <span className="stat-card__label">{t("affiliate.commissionRate")}</span>
          </div>
          <span className="stat-card__value">{summary.commission_percent}%</span>
        </div>
        <div className="stat-card">
          <div className="stat-card__top">
            <span className="icon-tile icon-tile--info">
              <Users size={18} />
            </span>
            <span className="stat-card__label">{t("affiliate.totalReferrals")}</span>
          </div>
          <span className="stat-card__value">{summary.total_referrals.toLocaleString()}</span>
        </div>
        <div className="stat-card">
          <div className="stat-card__top">
            <span className="icon-tile icon-tile--success">
              <Wallet size={18} />
            </span>
            <span className="stat-card__label">{t("affiliate.totalEarned")}</span>
          </div>
          <span className="stat-card__value">
            {money(summary.total_commission_earned)}
          </span>
        </div>
      </div>

      <section className="panel">
        <div className="panel-header">
          <span className="icon-tile">
            <Share2 size={18} />
          </span>
          <h2>{t("affiliate.yourLink")}</h2>
        </div>
        <div className="referral-link-box">
          <code>{referralLink}</code>
          <button className="btn-sm" onClick={copyLink}>
            {copied ? <Check size={14} /> : <Copy size={14} />}
            {copied ? t("common.copied") : t("common.copy")}
          </button>
        </div>
        <p className="field-hint">
          {t("affiliate.codeIs", { code: summary.referral_code })}
        </p>
      </section>

      <section className="panel">
        <div className="panel-header">
          <span className="icon-tile icon-tile--info">
            <Users size={18} />
          </span>
          <h2>{t("affiliate.yourReferrals")}</h2>
        </div>

        {!referrals || referrals.length === 0 ? (
          <div className="empty-state">
            <span className="empty-state__icon">
              <Share2 size={22} />
            </span>
            <h3>{t("affiliate.noReferrals")}</h3>
            <p>{t("affiliate.noReferralsBody")}</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("common.email")}</th>
                  <th>{t("affiliate.joined")}</th>
                  <th>{t("affiliate.ordersCol")}</th>
                  <th>{t("affiliate.commissionEarned")}</th>
                </tr>
              </thead>
              <tbody>
                {referrals.map((r) => (
                  <tr key={r.id}>
                    <td>{r.email}</td>
                    <td className="muted">{new Date(r.date_joined).toLocaleDateString()}</td>
                    <td>{r.orders_count}</td>
                    <td className="amount-positive">{money(r.commission_earned)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
