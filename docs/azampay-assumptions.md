# AzamPay integration — assumptions to verify

Phase 4 (`backend/apps/payments/gateways/azampay.py`) is built against
AzamPay's publicly documented flow. Confirm every field name below against
the real sandbox docs/response payloads before Phase 4 is considered done —
get sandbox credentials at https://developers.azampay.co.tz/.

## Assumed flow

1. **Token**: `POST {auth_base_url}/AppRegistration/GenerateToken` with
   `{appName, clientId, clientSecret}` → `{data: {accessToken, tokenType, expire}}`.
   Cache the bearer token (Redis) until shortly before `expire`.
2. **Mobile money checkout (collection)**:
   `POST {base_url}/azampay/mno/checkout` with
   `{accountNumber, amount, currency: "TZS", externalId, provider}`
   (`provider` ∈ `Mpesa | Tigo | Airtel | Halopesa`), `Authorization: Bearer <token>`.
   This triggers a USSD push to the customer's phone; the response only
   acknowledges the request was accepted — it does **not** carry the final
   payment result.
3. **Callback**: AzamPay POSTs the final result asynchronously to a URL you
   register with them (`backend/apps/payments/urls.py` →
   `/api/payments/webhooks/azampay/`). Expected fields (verify): `transactionstatus`
   (`success`/`failed`), `utilityref` or `externalId` (maps back to our
   `Transaction.internal_reference`), `msisdn`, `amount`, `reference` (AzamPay's
   own transaction id).

## What to confirm with AzamPay's real docs/sandbox

1. Exact callback payload field names and content type (JSON vs form).
2. Whether callbacks are signed (a header/secret to verify) or whether IP
   allowlisting is the only protection — if unsigned, treat the callback as
   "hint to poll" and confirm via a status-check call rather than trusting it blindly.
3. Card/bank checkout endpoint (separate from `mno/checkout`) for Phase 2
   payments work later.
4. Sandbox test MSISDNs/amounts that simulate success vs. failure.
5. Settlement/payout timing and any minimum transaction amount.

Once confirmed, only `azampay.py` needs to change — `BasePaymentGateway`,
`apps/payments/services.py`, and the wallet crediting logic stay the same.
