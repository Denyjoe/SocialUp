# Upstream provider — VinaSMM

Confirmed against https://vinasmm.com/api on 2026-09-04. Implemented in
[`backend/apps/providers/clients/jap_client.py`](../backend/apps/providers/clients/jap_client.py).

## Confirmed contract

- **Endpoint:** `POST https://vinasmm.com/api/v2` (single endpoint, form-encoded body, JSON response)
- **Auth:** `key` field in the POST body (no header auth)
- All requests include `key` and `action`.

| Action | Params | Response |
|---|---|---|
| `services` | — | array of `{service, name, type, category, rate, min, max, refill, cancel}` |
| `add` | `service`, `link`, `quantity` (+ variant params below) | `{"order": <id>}` |
| `status` | `order` (single) or `orders` (comma-separated, max 100) | single: `{charge, start_count, status, remains, currency}`. Multi: **not shown in the fetched docs — assumed to be a dict keyed by order id**, same per-order shape. Verify with a real 2+ order call before relying on it. |
| `refill` | `order` or `orders` (max 100) | single: `{"refill": "<id>"}`; multi: `[{"order": <id>, "refill": <id>}]` |
| `refill_status` | `refill` or `refills` | `{"status": "Completed"\|"Rejected"}` |
| `cancel` | `orders` (comma-separated, **always plural, even for one order**) | `[{"order": <id>, "cancel": <cancel_id>}]` |
| `balance` | — | `{"balance": "<amount>", "currency": "USD"}` |

`add` variant params by service type (only the default/quantity-based path is
wired into `JAPStyleClient` right now — see "Not yet built" below):
`quantity` (default) · `quantity, runs, interval` (drip-feed) ·
`comments` (custom comments, `\r\n`/`\n`-separated) · `usernames` (mentions) ·
`username, quantity` (custom list mentions) ·
`username, min, max, posts, old_posts, delay, expiry` (subscriptions) ·
`groups` (invites from groups).

Error shape: `{"error": "<description>"}`. No documented HTTP status code
convention or rate limits — `jap_client.py` treats any non-2xx HTTP response
*or* a 200 with an `error` key as `ProviderAPIError`.

## Still to verify once real credentials are in hand

1. **Multi-order `status` response shape** — confirm it's a dict keyed by
   order id (assumed) vs. a list.
2. **Full status value list** — docs only show `Partial | In progress |
   Completed`; real panels also return `Pending`, `Canceled`, `Processing`
   in practice. `_STATUS_MAP` in `apps/orders/tasks.py` already handles all
   of these defensively (unknown values fall back to `in_progress`), but
   confirm nothing is being silently miscategorized.
3. **Rate limits / recommended polling interval** for `status` with many orders.
4. **`cancel` semantics** — does the returned `cancel` id need a follow-up
   status check (like `refill_status`), or is it immediate? No
   `cancel_status` action is documented. `JAPStyleClient.cancel_order()`
   currently treats getting a `cancel` id back as success.

## Not yet built (future refinement, out of scope for Phase 3's baseline)

Only the default/quantity-based `add` variant is implemented. Custom
comments, mentions, drip-feed, and subscription order types exist in the
catalog's `service_type` field but don't yet have matching UI inputs or
`add_order(**kwargs)` wiring — add these when there's a concrete service of
that type to test against.
