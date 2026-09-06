# Security Policy

This project handles real money: customer wallets, provider orders, and crypto deposits through NOWPayments. Security reports are taken seriously.

## Reporting a vulnerability

Do not file a public issue for a security problem. Report it privately so it can be fixed before it is disclosed.

Email: report an issue to the maintainer through a private channel. You can reach the project author via their GitHub profile (https://github.com/denyjoe) using a private message or a directly provided contact address.

Please include:

- A description of the vulnerability and the impact
- The affected component (for example the payments webhook, the wallet service, or an API endpoint)
- Steps to reproduce, or a minimal proof of concept
- Your preferred contact method for follow-up

## What we consider in scope

- Anything under `backend/apps/payments/` (deposit creation, IPN webhook verification, mock gateway fallback)
- Wallet and ledger logic in `backend/apps/wallet/`
- Order creation and provider submission in `backend/apps/orders/`
- Authentication and account access in `backend/apps/accounts/`
- The public and reseller APIs in `backend/apps/panelapi/`

## What happens after you report

1. We acknowledge your report within 5 business days.
2. We investigate and, where needed, fix the issue and ship a patched release.
3. We agree on a coordinated disclosure timeline with you before the issue is made public.

## Responsible disclosure

Do not test against the live production environment. Use a local development setup, or ask for a staging environment. Do not access, copy, or modify data that does not belong to you while verifying an issue.

## Safe harbor

Research conducted in good faith, following this policy, will not be reported to third parties as a security incident. You can verify vulnerabilities against your own local copy of the codebase without restriction.