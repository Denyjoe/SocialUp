import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  BadgeCheck,
  Coins,
  KeyRound,
  Mail,
  Phone,
  ShieldAlert,
  User as UserIcon,
} from "lucide-react";

import { apiClient } from "../../api/client";
import { resendVerificationEmail } from "../../api/endpoints/auth";
import { useAuth } from "../../auth/AuthContext";
import { PhoneVerificationModal } from "../../components/PhoneVerificationModal";
import { useCurrency } from "../../currency/CurrencyContext";
import { extractErrorMessage } from "../../utils/errors";
import type { UserProfile } from "../../types/api";

/**
 * Account settings page. Manages verification, phone, password, and 2FA.
 */
export function SettingsPage() {
  const { t } = useTranslation();
  const { user, setUser } = useAuth();
  const [showPhoneModal, setShowPhoneModal] = useState(false);

  if (!user) return null;

  return (
    <>
      <div className="page-header-row">
        <h1>{t("settings.title")}</h1>
      </div>
      <p className="page-subtitle">{t("settings.securitySubtitle")}</p>

      <VerificationPanel user={user} onVerifyPhone={() => setShowPhoneModal(true)} />
      <PhonePanel user={user} onSaved={setUser} />
      <PreferencesPanel />
      <PasswordPanel />

      {showPhoneModal && <PhoneVerificationModal onClose={() => setShowPhoneModal(false)} />}
    </>
  );
}

// ── Verification Panel ──

function VerificationPanel({
  user,
  onVerifyPhone,
}: {
  user: UserProfile;
  onVerifyPhone: () => void;
}) {
  const { t } = useTranslation();
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resend = useMutation({
    mutationFn: resendVerificationEmail,
    onSuccess: () => setSent(true),
    onError: (err) => setError(extractErrorMessage(err, t("verify.couldNotResend"))),
  });

  return (
    <section className="panel">
      <div className="panel-header">
        <span className="icon-tile">
          <BadgeCheck size={18} />
        </span>
        <h2>{t("settings.verification")}</h2>
      </div>
      {error && <p className="form-error">{error}</p>}

      <div className="settings-row">
        <div className="row">
          <Mail size={16} className="muted" />
          <div>
            <strong>{t("common.email")}</strong>
            <div className="muted text-sm">{user.email}</div>
          </div>
        </div>
        {user.email_verified ? (
          <span className="status-badge status-badge--completed">{t("settings.verified")}</span>
        ) : (
          <div className="row">
            <span className="status-badge status-badge--pending">
              {t("settings.notVerified")}
            </span>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => resend.mutate()}
              disabled={resend.isPending || sent}
            >
              {sent ? t("settings.emailSent") : t("settings.resendEmail")}
            </button>
          </div>
        )}
      </div>

      <div className="settings-row">
        <div className="row">
          <Phone size={16} className="muted" />
          <div>
            <strong>{t("settings.phoneNumber")}</strong>
            <div className="muted text-sm">
              {user.phone_number || t("settings.notAddedYet")}
              <span className="badge" style={{ marginLeft: "0.4rem" }}>
                {t("common.optional")}
              </span>
            </div>
          </div>
        </div>
        {user.phone_verified ? (
          <span className="status-badge status-badge--completed">{t("settings.verified")}</span>
        ) : (
          <button type="button" className="btn-secondary btn-sm" onClick={onVerifyPhone}>
            {user.phone_number ? t("settings.verifyNumber") : t("settings.addNumber")}
          </button>
        )}
      </div>

      <p className="field-hint" style={{ marginTop: "0.75rem" }}>
        {t("settings.verificationNote")}
      </p>
    </section>
  );
}


// ── Phone Panel ──

function PhonePanel({ user, onSaved }: { user: UserProfile; onSaved: (u: UserProfile) => void }) {
  const { t } = useTranslation();
  const [phone, setPhone] = useState(user.phone_number);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: async (phone_number: string) => {
      const { data } = await apiClient.patch<UserProfile>("/auth/me/", { phone_number });
      return data;
    },
    onSuccess: (profile) => {
      onSaved(profile);
      setSaved(true);
      setError(null);
    },
    onError: (err) => setError(extractErrorMessage(err, t("settings.couldNotSavePhone"))),
  });

  return (
    <section className="panel">
      <div className="panel-header">
        <span className="icon-tile icon-tile--info">
          <UserIcon size={18} />
        </span>
        <h2>{t("settings.contactDetails")}</h2>
      </div>
      {saved && <p className="form-success">{t("settings.phoneSaved")}</p>}
      {error && <p className="form-error">{error}</p>}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setSaved(false);
          save.mutate(phone);
        }}
      >
        <label>
          {t("settings.phoneNumber")}
          <input
            type="tel"
            placeholder="+255…"
            value={phone}
            onChange={(e) => {
              setPhone(e.target.value);
              setSaved(false);
            }}
          />
          <span className="field-hint">{t("settings.phoneHint")}</span>
        </label>
        <button type="submit" disabled={save.isPending}>
          {save.isPending ? t("common.saving") : t("settings.saveChanges")}
        </button>
      </form>
    </section>
  );
}

// ── Preferences Panel ──

function PreferencesPanel() {
  const { t } = useTranslation();
  const { currency, setCurrency, supported, base } = useCurrency();

  return (
    <section className="panel">
      <div className="panel-header">
        <span className="icon-tile icon-tile--success">
          <Coins size={18} />
        </span>
        <h2>{t("settings.preferences")}</h2>
      </div>
      <label>
        {t("settings.displayCurrency")}
        <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
          {supported.map((code) => (
            <option key={code} value={code}>
              {code}
            </option>
          ))}
        </select>
        <span className="field-hint">{t("settings.currencyHint", { base })}</span>
      </label>
    </section>
  );
}

// ── Password Panel ──

function PasswordPanel() {
  const { t } = useTranslation();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const change = useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post("/auth/change-password/", {
        old_password: oldPassword,
        new_password: newPassword,
      });
      return data;
    },
    onSuccess: () => {
      setDone(true);
      setError(null);
      setOldPassword("");
      setNewPassword("");
      setConfirm("");
    },
    onError: (err) => setError(extractErrorMessage(err, t("settings.couldNotChangePassword"))),
  });

  return (
    <section className="panel">
      <div className="panel-header">
        <span className="icon-tile icon-tile--warning">
          <KeyRound size={18} />
        </span>
        <h2>{t("settings.password")}</h2>
      </div>
      {done && <p className="form-success">{t("settings.passwordUpdated")}</p>}
      {error && <p className="form-error">{error}</p>}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setDone(false);
          if (newPassword !== confirm) {
            setError(t("settings.passwordsDoNotMatch"));
            return;
          }
          change.mutate();
        }}
      >
        <label>
          {t("settings.currentPassword")}
          <input
            type="password"
            autoComplete="current-password"
            required
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
          />
        </label>
        <label>
          {t("settings.newPassword")}
          <input
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
        </label>
        <label>
          {t("settings.confirmNewPassword")}
          <input
            type="password"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        </label>
        <button type="submit" disabled={change.isPending}>
          {change.isPending ? t("common.saving") : t("settings.changePassword")}
        </button>
      </form>
      <p className="field-hint" style={{ marginTop: "0.75rem" }}>
        <ShieldAlert size={13} style={{ verticalAlign: "-2px" }} />{" "}
        {t("settings.googleNoPassword")}
      </p>
    </section>
  );
}
