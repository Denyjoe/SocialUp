import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { resendVerificationEmail } from "../api/endpoints/auth";
import { useAuth } from "../auth/AuthContext";
import { useTranslation } from "react-i18next";
import { extractErrorMessage } from "../utils/errors";

/** Only nags about email, the single gate on placing an order.
 * Phone is optional (used for sending order updates), so it is deliberately
 * never nagged about here, and Google sign-ins arrive already verified and
 * never see this banner at all. */
export function VerificationBanner() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [emailSent, setEmailSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resendMutation = useMutation({
    mutationFn: resendVerificationEmail,
    onSuccess: () => setEmailSent(true),
    onError: (err) => setError(extractErrorMessage(err, t("verify.couldNotResend"))),
  });

  if (!user || user.email_verified) return null;

  return (
    <div className="verification-banner">
      <span>
        {t("verify.emailBanner")}
      </span>
      <div className="verification-banner__actions">
        <button
          onClick={() => resendMutation.mutate()}
          disabled={resendMutation.isPending || emailSent}
        >
          {emailSent ? t("verify.emailSent") : resendMutation.isPending ? t("verify.sending") : t("verify.resendEmail")}
        </button>
      </div>
      {error && <span className="form-error">{error}</span>}
    </div>
  );
}
