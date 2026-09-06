import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { register as registerRequest } from "../../api/endpoints/auth";
import { useAuth } from "../../auth/AuthContext";
import { GoogleSignInButton } from "../../components/GoogleSignInButton";
import { TurnstileWidget } from "../../components/TurnstileWidget";
import { extractErrorMessage } from "../../utils/errors";

// Built inside the component so the validation messages follow the chosen language.
function buildSchema(t: (key: string) => string) {
  return z
    .object({
      email: z.string().email(t("auth.invalidEmail")),
      phone_number: z.string().optional(),
      password: z.string().min(8, t("auth.passwordMin")),
      confirm_password: z.string().min(1, t("auth.reenterPassword")),
      referral_code: z.string().optional(),
    })
    .refine((values) => values.password === values.confirm_password, {
      message: t("auth.passwordsMismatch"),
      path: ["confirm_password"],
    });
}

type FormValues = z.infer<ReturnType<typeof buildSchema>>;

export function RegisterPage() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [serverError, setServerError] = useState<string | null>(null);
  const [turnstileToken, setTurnstileToken] = useState("");
  const referralCode = params.get("ref") ?? "";

  const {
    register: registerField,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(buildSchema(t)),
    defaultValues: { referral_code: referralCode },
  });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    const { confirm_password: _confirm, ...payload } = values; // client-side check only
    try {
      await registerRequest({ ...payload, turnstile_token: turnstileToken });
      // Registration doesn't return tokens, so log in right after.
      await login({ email: values.email, password: values.password });
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setServerError(extractErrorMessage(err, t("auth.couldNotCreate")));
    }
  }

  return (
    <div className="auth-page">
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <h1>{t("auth.createAccount")}</h1>
        {serverError && <p className="form-error">{serverError}</p>}
        <label>
          {t("common.email")}
          <input type="email" autoComplete="email" {...registerField("email")} />
          {errors.email && <span className="field-error">{errors.email.message}</span>}
        </label>
        <label>
          {t("auth.phoneOptional")}
          <input type="tel" placeholder="+255…" {...registerField("phone_number")} />
          <span className="field-hint">{t("auth.phoneHint")}</span>
        </label>
        <label>
          {t("common.password")}
          <input type="password" autoComplete="new-password" {...registerField("password")} />
          {errors.password && <span className="field-error">{errors.password.message}</span>}
        </label>
        <label>
          {t("auth.confirmPassword")}
          <input
            type="password"
            autoComplete="new-password"
            {...registerField("confirm_password")}
          />
          {errors.confirm_password && (
            <span className="field-error">{errors.confirm_password.message}</span>
          )}
        </label>
        <label>
          {t("auth.referralOptional")}
          <input type="text" {...registerField("referral_code")} />
        </label>
        <TurnstileWidget onToken={setTurnstileToken} />
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? t("auth.creatingAccount") : t("auth.register")}
        </button>
        {import.meta.env.VITE_GOOGLE_CLIENT_ID && (
          <>
            <div className="auth-divider">
              <span>{t("auth.or")}</span>
            </div>
            <GoogleSignInButton
              referralCode={referralCode}
              onSuccess={() => navigate("/dashboard", { replace: true })}
              onError={setServerError}
            />
          </>
        )}
        <p className="auth-switch">
          {t("auth.haveAccount")} <Link to="/login">{t("auth.logIn")}</Link>
        </p>
      </form>
    </div>
  );
}
