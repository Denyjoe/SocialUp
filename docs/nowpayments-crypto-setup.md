# Crypto deposits via NOWPayments — setup

Interim deposit option while PesaPal (local Tanzanian mobile money/card)
verification is pending. Lets a customer top up their wallet with any coin
NOWPayments supports (BTC, USDT, etc.) through a hosted checkout page — no
crypto handling code lives in this app at all, NOWPayments does the
conversion and simply tells us "paid" or not via webhook.

Until real credentials are set, `NOWPAYMENTS_API_KEY`/`NOWPAYMENTS_IPN_SECRET`
are empty and every deposit falls back to a mock gateway that completes
instantly — this is what makes local dev and the automated test suite work
with zero external setup. Nothing below is required to keep building or
testing the rest of the app.

## How it works (for reference)

1. Customer enters a TZS amount on **Add Funds**. We convert it to USD (via
   the exchange-rate snapshot already used elsewhere in the app) and reject
   anything under NOWPayments' effective $5 minimum.
2. We create an `invoice` via NOWPayments' API and redirect the customer to
   the hosted `invoice_url` — that page handles coin selection, exact amount,
   and the payment address. We never touch a wallet address or private key.
3. NOWPayments POSTs a signed webhook to our backend as the payment
   progresses. We verify the signature, and only credit the wallet once the
   status reaches `finished` — a `partially_paid` payment is recorded but
   never auto-credited (NOWPayments' own documentation advises against it).
4. The TZS amount credited is the exact amount locked in at step 1, so a
   crypto price swing between checkout and confirmation never changes what
   the customer receives.

## Steps to activate it with real credentials

1. Sign up at https://nowpayments.io/ and complete their merchant
   verification (separate from, and unrelated to, PesaPal's).
2. In the NOWPayments dashboard, go to **Store settings → API keys** and
   create an API key.
3. Go to **Store settings → IPN (Instant Payment Notification)** and set the
   callback URL to:
   ```
   https://<your-public-backend-domain>/api/payments/webhooks/nowpayments/
   ```
   Copy the **IPN secret key** shown there (used to verify webhook
   signatures — different from the API key).
4. In `backend/.env`:
   ```
   NOWPAYMENTS_API_KEY=<your api key>
   NOWPAYMENTS_IPN_SECRET=<your ipn secret>
   ```
5. Restart the backend. Deposits now go through the real NOWPayments API
   instead of the mock gateway.

## Important: localhost cannot receive the webhook

NOWPayments calls the IPN URL over the public internet, so it cannot reach
`http://localhost:8000` — a deposit made against real credentials from a
local dev machine will sit in `waiting` forever with no way to confirm it.
This is purely a local-dev limitation, not a deployment one: once the
backend is actually deployed behind a real public HTTPS domain, it already
has a reachable URL and this stops being a concern at all — no tunnel of
any kind is needed in production.

The only time this needs a workaround is testing the *real* NOWPayments
flow before deployment, from a local machine. That needs some way to
expose `localhost:8000` at a temporary public HTTPS URL, with
`NOWPAYMENTS_IPN_CALLBACK_URL` pointed at it for the duration of the test.
Pick whatever tool fits — this is intentionally left open rather than
pinned to one vendor. Local development without this is still fully
testable via the mock gateway (leave the credentials unset).

## Currency note

The wallet always stays in TZS. NOWPayments is only ever shown a USD
amount for pricing; customers pick their own coin on the hosted checkout
page and NOWPayments converts it, we never see or store a coin-to-TZS rate.
