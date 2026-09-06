import { Link } from "react-router-dom";
import { ArrowRight, Code2 } from "lucide-react";
import { Trans, useTranslation } from "react-i18next";

import { PANEL_API_ACTIONS, PANEL_API_ENDPOINT } from "../../data/panelApiDocs";

export function ApiDocsPage() {
  const { t } = useTranslation();

  return (
    <div className="public-page">
      <div className="page-header-row">
        <span className="icon-tile">
          <Code2 size={18} />
        </span>
        <h1>{t("api.title")}</h1>
      </div>
      <p className="page-subtitle">{t("apiDocs.subtitle")}</p>

      <section className="panel">
        <h2>{t("api.makingRequests")}</h2>
        <p className="muted">
          <Trans
            i18nKey="apiDocs.requestIntro"
            values={{ endpoint: PANEL_API_ENDPOINT }}
            components={{ c: <code /> }}
          />
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
          {t("apiDocs.exampleRequest")}
        </p>
        <pre className="code-block">
          <code>{`curl -X POST ${PANEL_API_ENDPOINT} \\\n  -d key=YOUR_API_KEY \\\n  -d action=add \\\n  -d service=1 \\\n  -d link=https://instagram.com/yourprofile \\\n  -d quantity=1000`}</code>
        </pre>
      </section>

      <section className="cta-large">
        <h2>{t("apiDocs.getKeyTitle")}</h2>
        <p className="muted">{t("apiDocs.getKeyBody")}</p>
        <Link to="/register" className="btn">
          {t("auth.createAccount")} <ArrowRight size={16} />
        </Link>
      </section>
    </div>
  );
}
