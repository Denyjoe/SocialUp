import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { useAuth } from "../../auth/AuthContext";
import { GoogleSignInButton } from "../../components/GoogleSignInButton";
import { extractErrorMessage } from "../../utils/errors";
import { useTranslation } from "react-i18next";

const schema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});

type FormValues = z.infer<typeof schema>;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState<string | null>(null);
  const { t } = useTranslation();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await login(values);
      const redirectTo = (location.state as { from?: string } | null)?.from ?? "/dashboard";
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setServerError(extractErrorMessage(err, t("auth.invalidCredentials")));
    }
  }

  return (
    <div className="auth-page">
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <h1>{t("auth.logIn")}</h1>
        {serverError && <p className="form-error">{serverError}</p>}
        <label>
          {t("common.email")}
          <input type="email" autoComplete="email" {...register("email")} />
          {errors.email && <span className="field-error">{errors.email.message}</span>}
        </label>
        <label>
          {t("common.password")}
          <input type="password" autoComplete="current-password" {...register("password")} />
          {errors.password && <span className="field-error">{errors.password.message}</span>}
        </label>
        <p className="auth-forgot">
          <Link to="/forgot-password">{t("auth.forgotPassword")}</Link>
        </p>
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? t("auth.loggingIn") : t("auth.logIn")}
        </button>
        {import.meta.env.VITE_GOOGLE_CLIENT_ID && (
          <>
            <div className="auth-divider">
              <span>or</span>
            </div>
            <GoogleSignInButton
              onSuccess={() => {
                const redirectTo = (location.state as { from?: string } | null)?.from ?? "/dashboard";
                navigate(redirectTo, { replace: true });
              }}
              onError={setServerError}
            />
          </>
        )}
        <p className="auth-switch">
          {t("auth.noAccount")} <Link to="/register">{t("auth.register")}</Link>
        </p>
      </form>
    </div>
  );
}

