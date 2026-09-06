# Beem Africa OTP — assumptions to verify

Confirmed against https://docs.beem.africa/api-reference/ on 2026-09-04.
Implemented in
[`backend/apps/accounts/phone_otp.py`](../backend/apps/accounts/phone_otp.py).
Chosen over Firebase Phone Auth (which has a
[documented history of failing to deliver OTPs to Tanzanian numbers](https://github.com/firebase/quickstart-android/issues/791))
and over Twilio Verify (routes through aggregators in Africa rather than
direct telco connections) — Beem is Tanzania-native with direct carrier links.

## Confirmed contract

- **Send:** `POST https://apiotp.beem.africa/v1/request` — Basic Auth (`api_key`:`secret_key`). Body: `{"appId": ..., "msisdn": "..."}`. Response: `{"data": {"pinId": "<uuid>", "message": {"code": 100, "message": "..."}, "pinExpiryTimeInMinutes": N, "expiresInSeconds": N}}` — `code: 100` = sent.
- **Verify:** `POST https://apiotp.beem.africa/v1/verify` (staging: `https://dev-otp.beem.africa/v1/verify`) — same auth. Response: `{"data": {"message": {"code": 117, "message": "..."}}}` — `code: 117` = valid PIN. Errors return HTTP 403 with the same shape.

## Real error encountered (2026-09-04) — AUTH_INVALID_CREDENTIALS

Live test against `/v1/request` returned HTTP 401:
```json
{"code": 120, "error_code": "AUTH_INVALID_CREDENTIALS", "message": "Invalid api_key and/or secret_id"}
```
This confirms a **new error shape** for auth failures specifically — flat
(`code`/`error_code`/`message` at the top level), not wrapped in `{"data":
...}` like the success/logical-error shapes documented above.
`BeemOTPClient._post()` already handles this correctly (any non-2xx response
without a `data` key raises `PhoneOTPError` with the raw body), so no code
change was needed for the error itself to surface properly — the credentials
were the actual problem, confirmed via further research:

**Root cause: OTP has its own separate API key/secret, distinct from Beem's
general SMS API credentials.** If you already had a Beem account for SMS,
reusing those credentials for OTP causes exactly this error. Get the
OTP-specific pair from your dashboard: **OTP → API Set up → Reset** (not the
general SMS API credentials page). The secret is shown only once — if
you've already generated one and lost it, click Reset again for a fresh
pair, then update `BEEM_SECRET_KEY` in `backend/.env`.

## Still to verify once real credentials are in hand

1. **The exact field name for the code on the verify call.** The fetched docs didn't show a full example — `phone_otp.py` currently sends `{"pinId": ..., "pin": "<code>"}` (assumed `pin`; could be `otp` or `code`). Test one real send+verify round trip and fix if wrong.
2. **Any other required fields on `/request`** beyond `appId`/`msisdn` — confirm against the real API Explorer at https://docs.beem.africa/.
3. **Rate limits** on `/request` (relevant to `OTP_SEND_COOLDOWN` in `apps/accounts/views.py`, currently a conservative 60s local cooldown).
4. **WhatsApp delivery channel** — Beem's OTP API also supports WhatsApp per their guide; not wired up here, SMS-only for now.

## Setup

1. Sign up at https://beem.africa (free developer tier) or log in if you already have an account.
2. Go to **OTP → API Set up → Reset** on your dashboard — this generates OTP-specific `API key` + `Secret key` (**do not** reuse general SMS API credentials here, see above). Copy the secret immediately; it's shown once.
3. Get your `appId` from the same OTP setup section.
4. Add to `backend/.env`: `BEEM_API_KEY`, `BEEM_SECRET_KEY`, `BEEM_APP_ID`.
5. Send yourself a real test OTP via the "Verify phone" flow in the dashboard and confirm the code arrives. If the *send* step now works but *verify* fails with a code you know is correct, that's assumption #1 above (the code field name) — fix it in `phone_otp.py`.
