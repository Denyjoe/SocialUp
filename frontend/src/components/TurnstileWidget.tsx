import { useEffect, useRef } from "react";

import { useExternalScript } from "../hooks/useExternalScript";

const SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY;

export function TurnstileWidget({ onToken }: { onToken: (token: string) => void }) {
  const loaded = useExternalScript(
    SITE_KEY ? "https://challenges.cloudflare.com/turnstile/v0/api.js" : null
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const renderedRef = useRef(false);

  useEffect(() => {
    if (!loaded || !SITE_KEY || !containerRef.current || renderedRef.current || !window.turnstile) return;
    window.turnstile.render(containerRef.current, { sitekey: SITE_KEY, callback: onToken });
    renderedRef.current = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded]);

  if (!SITE_KEY) return null; // Turnstile not configured on this deployment; the backend allows it through

  return <div ref={containerRef} className="turnstile-widget" />;
}
