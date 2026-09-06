import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { verifyEmail } from "../../api/endpoints/auth";
import { extractErrorMessage } from "../../utils/errors";
import { useTranslation } from "react-i18next";

export function VerifyEmailPage() {
  const [params] = useSearchParams();
  const { t } = useTranslation();
  const token = params.get("token");
  const [state, setState] = useState<"pending" | "success" | "error">("pending");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setState("error");
      setError("This verification link is missing its token.");
      return;
    }
    verifyEmail(token)
      .then(() => setState("success"))
      .catch((err) => {
        setState("error");
        setError(extractErrorMessage(err, t("auth.linkInvalidOrExpired")));
      });
  }, [token]);

  return (
    <div className="auth-page">
      <div className="verify-email-card">
        {state === "pending" && <p>{t("auth.verifyingEmail")}</p>}
        {state === "success" && (
          <>
            <h1>{t("auth.emailVerified")}</h1>
            <p>{t("auth.emailConfirmed")}</p>
          </>
        )}
        {state === "error" && (
          <>
            <h1>{t("auth.verificationFailed")}</h1>
            <p className="form-error">{error}</p>
          </>
        )}
        <p className="auth-switch">
          <Link to="/dashboard">{t("auth.goToDashboard")}</Link>
        </p>
      </div>
    </div>
  );
}
