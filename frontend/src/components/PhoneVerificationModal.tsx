import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { sendPhoneOtp, verifyPhoneOtp } from "../api/endpoints/auth";
import { useAuth } from "../auth/AuthContext";
import { extractErrorMessage } from "../utils/errors";
import { Modal } from "./Modal";
import { useTranslation } from "react-i18next";

export function PhoneVerificationModal({ onClose }: { onClose: () => void }) {
  const { user, setUser } = useAuth();
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [phoneNumber, setPhoneNumber] = useState(user?.phone_number ?? "");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const sendMutation = useMutation({
    mutationFn: () => sendPhoneOtp(phoneNumber),
    onSuccess: (data) => {
      setError(null);
      setInfo(data.detail);
      setStep("code");
    },
    onError: (err) => setError(extractErrorMessage(err, t("verify.couldNotSendCode"))),
  });

  const verifyMutation = useMutation({
    mutationFn: () => verifyPhoneOtp(code),
    onSuccess: () => {
      if (user) setUser({ ...user, phone_verified: true, phone_number: phoneNumber });
      queryClient.invalidateQueries({ queryKey: ["auth-me"] });
      onClose();
    },
    onError: (err) => setError(extractErrorMessage(err, t("verify.incorrectCode"))),
  });

  return (
    <Modal title={t("verify.phoneTitle")} onClose={onClose}>
      {step === "phone" ? (
        <form
          className="modal-form"
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            sendMutation.mutate();
          }}
        >
          {error && <p className="form-error">{error}</p>}
          <label>
            {t("settings.phoneNumber")}
            <input
              type="tel"
              required
              placeholder="+255…"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
            />
          </label>
          <button type="submit" disabled={sendMutation.isPending}>
            {sendMutation.isPending ? t("verify.sending") : t("verify.sendCode")}
          </button>
        </form>
      ) : (
        <form
          className="modal-form"
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            verifyMutation.mutate();
          }}
        >
          {info && <p className="form-success">{info}</p>}
          {error && <p className="form-error">{error}</p>}
          <label>
            {t("verify.enterCodeSent", { phone: phoneNumber })}
            <input
              type="text"
              inputMode="numeric"
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
          </label>
          <button type="submit" disabled={verifyMutation.isPending}>
            {verifyMutation.isPending ? t("verify.verifying") : t("verify.verify")}
          </button>
          <button
            type="button"
            className="link-button"
            onClick={() => {
              setStep("phone");
              setError(null);
            }}
          >
            {t("verify.useDifferentNumber")}
          </button>
        </form>
      )}
    </Modal>
  );
}
