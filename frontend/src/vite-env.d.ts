/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_GOOGLE_CLIENT_ID?: string;
  readonly VITE_TURNSTILE_SITE_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Minimal ambient typing for the third-party globals injected by
// components/GoogleSignInButton.tsx and components/TurnstileWidget.tsx —
// no official first-party types package for either.
interface Window {
  google?: {
    accounts: {
      id: {
        initialize(config: { client_id: string; callback: (response: { credential: string }) => void }): void;
        renderButton(parent: HTMLElement, options: Record<string, unknown>): void;
      };
    };
  };
  turnstile?: {
    render(container: HTMLElement, options: { sitekey: string; callback: (token: string) => void }): string;
    reset(widgetId?: string): void;
  };
}
