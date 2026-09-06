import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Check, Copy, Code2, KeyRound, RefreshCw } from "lucide-react";

import { fetchApiKey, regenerateApiKey } from "../../api/endpoints/auth";
import { PANEL_API_ACTIONS, PANEL_API_ENDPOINT } from "../../data/panelApiDocs";
import { useTranslation } from "react-i18next";

export function ApiPage() {
  const queryClient = useQueryClient();
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const { data: apiKey, isLoading } = useQuery({ queryKey: ["api-key"], queryFn: fetchApiKey });

  const regenerate = useMutation({
    mutationFn: regenerateApiKey,
    onSuccess: (newKey) => queryClient.setQueryData(["api-key"], newKey),
  });

  function copyKey() {
    if (!apiKey) return;
    navigator.clipboard.writeText(apiKey).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <>
      <div className="page-header-row">
        <h1>{t("api.title")}</h1>
      </div>
      <p className="page-subtitle">
        {t("api.subtitle")}
      </p>

      <section className="panel">
        <div className="panel-header">
          <span className="icon-tile icon-tile--warning">
            <KeyRound size={18} />
          </span>
          <h2>{t("api.yourKey")}</h2>
        </div>
        <div className="api-key-box">
          <code>{isLoading ? t("common.loading") : apiKey}</code>
          <button className="btn-ghost btn-icon" onClick={copyKey} aria-label={t("api.copyKey")}>
            {copied ? <Check size={15} /> : <Copy size={15} />}
          </button>
        </div>
        <div className="row" style={{ marginTop: "0.75rem" }}>
          <button
            className="btn-secondary btn-sm"
            onClick={() => regenerate.mutate()}
            disabled={regenerate.isPending}
          >
            <RefreshCw size={14} />
            {regenerate.isPending ? t("api.regenerating") : t("api.regenerate")}
          </button>
          <span className="field-hint" style={{ marginTop: 0 }}>
            {t("api.regenerateWarning")}
          </span>
        </div>
        {regenerate.isError && <p className="form-error">{t("api.couldNotRegenerate")}</p>}
      </section>

      <section className="panel">
        <div className="panel-header">
          <span className="icon-tile">
            <Code2 size={18} />
          </span>
          <h2>{t("api.makingRequests")}</h2>
        </div>
        <p className="muted">
          Send a <code>POST</code> to <code>{PANEL_API_ENDPOINT}</code> with either a form encoded
          or JSON body, always including your <code>key</code> and an <code>action</code>.
        </p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("api.action")}</th>
                <th>{t("api.parameters")}</th>
                <th>{t("api.description")}</th>
              </tr>
            </thead>
            <tbody>
              {PANEL_API_ACTIONS.map((a) => (
                <tr key={a.action}>
                  <td>
                    <code>{a.action}</code>
                  </td>
                  <td className="muted">{t(a.paramsKey)}</td>
                  <td>{t(a.descriptionKey)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="muted" style={{ marginTop: "1rem" }}>
          {t("api.exampleCurl")}
        </p>
        <pre className="code-block">
          <code>{`curl -X POST ${PANEL_API_ENDPOINT} \\\n  -d key=${apiKey ?? "YOUR_API_KEY"} \\\n  -d action=add \\\n  -d service=1 \\\n  -d link=https://instagram.com/yourprofile \\\n  -d quantity=1000`}</code>
        </pre>
      </section>
    </>
  );
}
