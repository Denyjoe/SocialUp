import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext";
import { useExternalScript } from "../hooks/useExternalScript";
import { extractErrorMessage } from "../utils/errors";

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

export function GoogleSignInButton({
  referralCode,
  onSuccess,
  onError,
}: {
  referralCode?: string;
  onSuccess: () => void;
  onError?: (message: string) => void;
}) {
  const { t } = useTranslation();
  const { loginWithGoogle } = useAuth();
  const loaded = useExternalScript(CLIENT_ID ? "https://accounts.google.com/gsi/client" : null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [rendered, setRendered] = useState(false);

  useEffect(() => {
    if (!loaded || !CLIENT_ID || !containerRef.current || rendered || !window.google) return;

    window.google.accounts.id.initialize({
      client_id: CLIENT_ID,
      callback: async (response: { credential: string }) => {
        try {
          await loginWithGoogle(response.credential, referralCode);
          onSuccess();
        } catch (err) {
          onError?.(extractErrorMessage(err, t("auth.googleFailed")));
        }
      },
    });
    window.google.accounts.id.renderButton(containerRef.current, {
      theme: "outline",
      size: "large",
      width: 320,
    });
    setRendered(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, rendered]);

  if (!CLIENT_ID) return null; // Google sign-in not configured on this deployment

  return <div ref={containerRef} className="google-signin-button" />;
}
