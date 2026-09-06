import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { confirmPasswordReset } from "../../api/endpoints/auth";
import { extractErrorMessage } from "../../utils/errors";

// Built inside the component so the validation messages follow the chosen language.
function buildSchema(t: (key: string) => string) {
  return z
    .object({
      new_password: z.string().min(8, t("auth.passwordMin")),
      confirm_password: z.string().min(1, t("auth.reenterPassword")),
    })
    .refine((values) => values.new_password === values.confirm_password, {
      message: t("auth.passwordsMismatch"),
      path: ["confirm_password"],
    });
}

type FormValues = z.infer<ReturnType<typeof buildSchema>>;

export function ResetPasswordPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const uid = params.get("uid");
  const token = params.get("token");
  const [serverError, setServerError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(buildSchema(t)) });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    if (!uid || !token) {
      setServerError(t("auth.resetLinkIncomplete"));
      return;
    }
    try {
      await confirmPasswordReset({ uid, token, new_password: values.new_password });
      setDone(true);
      setTimeout(() => navigate("/login", { replace: true }), 2000);
    } catch (err) {
      setServerError(extractErrorMessage(err, t("auth.couldNotReset")));
    }
  }

  if (!uid || !token) {
    return (
      <div className="auth-page">
        <div className="verify-email-card">
          <h1>{t("auth.invalidResetLink")}</h1>
          <p className="form-error">{t("auth.resetLinkMissing")}</p>
          <p className="auth-switch">
            <Link to="/forgot-password">{t("auth.requestNewLink")}</Link>
          </p>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="auth-page">
        <div className="verify-email-card">
          <h1>{t("auth.passwordUpdated")}</h1>
          <p>{t("auth.takingYouToLogin")}</p>
          <p className="auth-switch">
            <Link to="/login">{t("auth.logInNow")}</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <h1>{t("auth.setNewPassword")}</h1>
        {serverError && <p className="form-error">{serverError}</p>}
        <label>
          {t("auth.newPassword")}
          <input type="password" autoComplete="new-password" {...register("new_password")} />
          {errors.new_password && (
            <span className="field-error">{errors.new_password.message}</span>
          )}
        </label>
        <label>
          {t("auth.confirmNewPassword")}
          <input type="password" autoComplete="new-password" {...register("confirm_password")} />
          {errors.confirm_password && (
            <span className="field-error">{errors.confirm_password.message}</span>
          )}
        </label>
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? t("common.saving") : t("auth.setNewPassword")}
        </button>
        <p className="auth-switch">
          <Link to="/login">{t("auth.backToLogin")}</Link>
        </p>
      </form>
    </div>
  );
}
