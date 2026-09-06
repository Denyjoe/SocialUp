import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { requestPasswordReset } from "../../api/endpoints/auth";
import { extractErrorMessage } from "../../utils/errors";
import { useTranslation } from "react-i18next";

const schema = z.object({
  email: z.string().email("Enter a valid email address."),
});

type FormValues = z.infer<typeof schema>;

export function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const { t } = useTranslation();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await requestPasswordReset(values.email);
      setSent(true);
    } catch (err) {
      setServerError(extractErrorMessage(err, t("auth.couldNotSendReset")));
    }
  }

  if (sent) {
    return (
      <div className="auth-page">
        <div className="verify-email-card">
          <h1>{t("auth.checkEmail")}</h1>
          <p>
            {t("auth.resetSent")}
          </p>
          <p className="auth-switch">
            <Link to="/login">{t("auth.backToLogin")}</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <h1>{t("auth.resetTitle")}</h1>
        <p className="form-hint">
          {t("auth.resetHint")}
        </p>
        {serverError && <p className="form-error">{serverError}</p>}
        <label>
          {t("common.email")}
          <input type="email" autoComplete="email" {...register("email")} />
          {errors.email && <span className="field-error">{errors.email.message}</span>}
        </label>
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? t("verify.sending") : t("auth.sendResetLink")}
        </button>
        <p className="auth-switch">
          <Link to="/login">{t("auth.backToLogin")}</Link>
        </p>
      </form>
    </div>
  );
}
