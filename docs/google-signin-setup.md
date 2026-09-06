# Google Sign-In — setup

Direct Google OAuth (via the `google-auth` Python library), not Firebase —
see the Phase 7 discussion for why. Free, no Google Cloud billing required
for basic sign-in.

## Steps

1. Go to https://console.cloud.google.com/ and create a project (or use an existing one).
2. **APIs & Services → OAuth consent screen** — configure it (External user type is fine for a public panel), fill in the app name/support email, add your domain once you have one.
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
   - Application type: **Web application**.
   - **Authorized JavaScript origins**: add `http://localhost:5173` for local dev, and your real domain(s) once deployed.
   - You do **not** need to set a redirect URI — the Google Identity Services button flow used here doesn't redirect, it posts an ID token directly to our backend.
4. Copy the generated **Client ID** (looks like `1234567890-abc...apps.googleusercontent.com`).
5. Set it in **two** places (frontend and backend need the same value):
   - `backend/.env`: `GOOGLE_OAUTH_CLIENT_ID=<client id>`
   - `frontend/.env`: `VITE_GOOGLE_CLIENT_ID=<client id>`
6. Restart both dev servers. The "Sign in with Google" button appears automatically on the Login and Register pages once `VITE_GOOGLE_CLIENT_ID` is set — it's hidden entirely when unset.

No client secret is needed for this flow (ID-token verification only, no
server-side authorization code exchange).

## Troubleshooting

### `Error 400: origin_mismatch`

> Access blocked: Authorization Error. You can't sign in to this app because
> it doesn't comply with Google's OAuth 2.0 policy.

The page you are signing in from is not listed under **Authorized
JavaScript origins** for this OAuth client. Google compares the origin
exactly, so scheme, host and port all have to match.

Fix it in **Google Cloud Console → APIs & Services → Credentials →** your
OAuth client → **Authorized JavaScript origins → Add URI**:

```
http://localhost:5173
```

Points that catch people out:

- No trailing slash. `http://localhost:5173/` is rejected.
- No path. Just the origin.
- `http://127.0.0.1:5173` is a **different origin** to
  `http://localhost:5173`. If you ever open the app on the IP form, add
  both entries.
- The Vite port must match. If Vite falls back to 5174 because 5173 is
  taken, that origin needs adding too.
- Changes can take a few minutes to propagate. Retry in a private window
  to avoid a cached response.

Add each production domain the same way when you deploy, for example
`https://yourpanel.com`.

### `redirect_uri_mismatch`

Not applicable to this integration. The Google Identity Services button
posts an ID token straight to our backend and never redirects, so the
**Authorized redirect URIs** list can stay empty.
