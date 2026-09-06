# Cloudflare Turnstile — setup

Bot-defense on the registration form — stops scripted mass-registration
before it even reaches the email/phone verification steps (which cost real
money per SMS). Free, no Cloudflare paid plan required.

## Steps

1. Go to https://dash.cloudflare.com/ (free account is fine) → **Turnstile**.
2. **Add a site** — give it a name, add your domain(s) (`localhost` is allowed for local dev).
3. Choose widget mode — "Managed" is the recommended default (invisible unless Cloudflare suspects a bot).
4. Copy the **Site Key** and **Secret Key**.
5. Set:
   - `backend/.env`: `TURNSTILE_ENABLED=True`, `TURNSTILE_SECRET_KEY=<secret key>`
   - `frontend/.env`: `VITE_TURNSTILE_SITE_KEY=<site key>`
6. Restart both dev servers. The widget renders automatically on the Register page once `VITE_TURNSTILE_SITE_KEY` is set.

Until you do this, `TURNSTILE_ENABLED` defaults to `False` and registration
works with no bot-check at all — fine for local development, **not
recommended before a public launch**.
