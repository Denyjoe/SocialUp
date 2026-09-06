import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchAdminAffiliateSettings, updateAdminAffiliateSettings } from "../../api/endpoints/admin/affiliate";
import { fetchPlatformSettings, updatePlatformSettings } from "../../api/endpoints/admin/catalog";
import { extractErrorMessage } from "../../utils/errors";

export function SettingsAdminPage() {
  return (
    <div className="admin-settings-page">
      <div className="page-header-row">
        <h1>Settings</h1>
      </div>
      <p className="page-subtitle">Pricing defaults and affiliate commission.</p>
      <PricingSettingsPanel />
      <AffiliateSettingsPanel />
    </div>
  );
}

function PricingSettingsPanel() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "platform-settings"],
    queryFn: fetchPlatformSettings,
  });

  const [fxRate, setFxRate] = useState("");
  const [markup, setMarkup] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) {
      setFxRate(data.usd_to_local_rate);
      setMarkup(data.default_markup_percent);
    }
  }, [data]);

  const mutation = useMutation({
    mutationFn: () =>
      updatePlatformSettings({ usd_to_local_rate: fxRate, default_markup_percent: markup }),
    onSuccess: () => {
      setSaved(true);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["admin", "platform-settings"] });
      setTimeout(() => setSaved(false), 3000);
    },
    onError: (err) => setError(extractErrorMessage(err, "Could not save settings.")),
  });

  if (isLoading) return <p>Loading pricing settings…</p>;

  return (
    <section className="panel">
      <h2>Pricing</h2>
      <p className="muted">
        The exchange rate below converts every service's provider cost (in USD) into your local
        currency, and is used everywhere pricing happens. The markup is the fallback used when a
        service has no price of its own and no Pricing Rule matches it. Manual per-service prices
        and Pricing Rules both take priority over this default: see{" "}
        <Link to="/admin/pricing-rules">Pricing Rules</Link> to price a category, platform, or cost
        range differently instead of one flat percentage for everything.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
        className="modal-form"
        style={{ maxWidth: "24rem" }}
      >
        {error && <p className="form-error">{error}</p>}
        {saved && <p className="form-success">Saved.</p>}
        <label>
          USD → local currency rate
          <input type="number" step="0.0001" value={fxRate} onChange={(e) => setFxRate(e.target.value)} />
        </label>
        <label>
          Default markup (%)
          <input type="number" step="0.01" value={markup} onChange={(e) => setMarkup(e.target.value)} />
        </label>
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Save"}
        </button>
      </form>
    </section>
  );
}

function AffiliateSettingsPanel() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "affiliate-settings"],
    queryFn: fetchAdminAffiliateSettings,
  });

  const [commissionPercent, setCommissionPercent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) setCommissionPercent(data.commission_percent);
  }, [data]);

  const mutation = useMutation({
    mutationFn: () => updateAdminAffiliateSettings(commissionPercent),
    onSuccess: () => {
      setSaved(true);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["admin", "affiliate-settings"] });
      setTimeout(() => setSaved(false), 3000);
    },
    onError: (err) => setError(extractErrorMessage(err, "Could not save settings.")),
  });

  if (isLoading) return <p>Loading affiliate settings…</p>;

  return (
    <section className="panel">
      <h2>Affiliate program</h2>
      <p className="muted">
        Commission is credited straight to a referrer's wallet the moment their referral's order
        completes.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
        className="modal-form"
        style={{ maxWidth: "24rem" }}
      >
        {error && <p className="form-error">{error}</p>}
        {saved && <p className="form-success">Saved.</p>}
        <label>
          Commission (%)
          <input
            type="number"
            step="0.01"
            value={commissionPercent}
            onChange={(e) => setCommissionPercent(e.target.value)}
          />
        </label>
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Save"}
        </button>
      </form>
    </section>
  );
}
