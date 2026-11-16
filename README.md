# SocialUp

A self-serve social media growth platform. Customers fund a wallet and order SMM services (followers, views, likes and more) from an auto-synced catalog, with real crypto deposit support.

![Python](https://img.shields.io/badge/Python-3.x-3776AB)
![Django](https://img.shields.io/badge/Django-5.1-092E20)
![Django REST framework](https://img.shields.io/badge/DRF-3.15-red)
![React](https://img.shields.io/badge/React-18-61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6)
![Vite](https://img.shields.io/badge/Vite-5-646CFF)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Overview

SocialUp is a wallet-funded SMM panel built for the Tanzanian market. All money on the platform is stored in Tanzanian shillings (TZS); USD, EUR, GBP and other currencies are shown for convenience only and never change what a customer is charged.

The backend is a Django REST API. It manages accounts, an immutable wallet ledger, order creation and status tracking, a live service catalog synced from an upstream SMM provider, support tickets, an affiliate system, coupons and announcements, and an admin dashboard for running the whole business. Background jobs run on Celery with Redis.

The frontend is a React single-page app with a mobile-first responsive layout: an off-canvas navigation drawer and bottom tab bar on phones, a permanent sidebar on desktop, and light and dark themes with full localization (English, Swahili, Spanish, French, Arabic with RTL).

## Features

- Email and password accounts with JWT auth, email verification links, forgot/reset password, disposable-email blocking at signup, an opt-in Google Sign-In (direct OAuth, no Firebase), and optional Cloudflare Turnstile bot defense.
- Wallet system with an append-only ledger. Every credit and debit is a ledger entry, so the balance is always auditable and the ledger is the source of truth.
- Order pipeline that debits the wallet, submits the order to a provider client, and tracks status through to completion. A scheduled task keeps orders in sync with the upstream provider and retries stuck submissions.
- Live service catalog synced from VinaSMM over their JAP-style API (1,900+ services across 200+ categories when last synced), auto-priced into TZS.
- Configurable pricing rules: a per-category, per-platform or cost-range markup with an optional minimum-profit floor, plus manual per-service price overrides. A "reprice from rules" action sweeps the whole catalog on demand.
- Crypto deposits through NOWPayments, with IPN webhook verification and an instant mock gateway as a development fallback. Customers get a deposit history table.
- Support tickets with a message thread and automatic status transitions (open, answered, pending, closed).
- Affiliate system: a referrer earns commission on every completed referred order, credited to their wallet automatically and idempotently.
- Coupon codes (percent or fixed, with caps, usage limits and expiry) and dashboard announcements.
- Reseller API: a simple JAP-compatible endpoint so customers can automate orders with an API key.
- Admin area: revenue, cost and profit reports with CSV export, profitability by platform and category, catalog pricing health bands, users, services, pricing rules, providers, orders, wallet ledger, coupons, announcements and settings.
- Localized UI in five languages (English, Swahili, Spanish, French, Arabic with RTL) with a language switcher for signed-out visitors.

## Tech stack

| Layer    | Technology |
| -------- | ---------- |
| Backend  | Python, Django 5.1, Django REST framework, SimpleJWT |
| API docs | drf-spectacular (OpenAPI schema served from the backend) |
| Database | PostgreSQL 16 (SQLite works for local testing) |
| Queue    | Celery 5 + Redis 7 |
| Frontend | React 18, TypeScript, Vite 5, React Router, TanStack Query, React Hook Form + Zod |
| Payments | NOWPayments (crypto) with a mock gateway fallback |
| Provider | VinaSMM JAP-style HTTP client with a mock client fallback |
| i18n     | i18next (en, sw, es, fr, ar) |
| Deploy   | Docker Compose (backend, postgres, redis, celery worker, celery beat, frontend) |

## Getting started

### Option A: Docker (matches production topology)

Requires Docker Desktop (on Windows, with the WSL2 backend)

```bash
docker compose up --build
```

First time only, run migrations and create an admin user:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api
- API schema/docs: http://localhost:8000/api/docs/
- Django admin: http://localhost:8000/admin/

### Option B: Native, no Docker, SQLite

Good for quick backend work without external services.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate              # Windows PowerShell
pip install -r requirements-dev.txt
python manage.py migrate            # creates a local db.sqlite3
python manage.py createsuperuser
python manage.py seed_demo_services # populate a demo catalog (mock provider)
python manage.py credit_wallet you@example.com 200000
python manage.py runserver
```

Orders submit to the mock provider and complete instantly. Without a database server, Celery runs in eager mode, so there is nothing extra to start.

```bash
cd frontend
npm install
npm run dev
```

### Option C: Native, native PostgreSQL

Same as Option B but point `DATABASE_URL` in `backend/.env` at a local PostgreSQL install:

```
DATABASE_URL=postgres://user:password@localhost:5432/socialup
```

Percent-encode special characters in the password (`#` becomes `%23`). Postgres 15+ also no longer grants `CREATE` on the public schema by default, so a fresh database may need `ALTER DATABASE "<db>" OWNER TO <role>;` before migrations work.

### Environment files

Copy the examples and fill in real values. Never commit the real `.env` files.

```bash
cp backend/.env.example backend/.env       # Windows: copy backend\.env.example backend\.env
cp frontend/.env.example frontend/.env     # Windows: copy frontend\.env.example frontend\.env
```

Everything in the app works with only `DJANGO_SETTINGS_MODULE`, `SECRET_KEY` and `DEBUG` set. The rest are integrations: VinaSMM provider key, NOWPayments key and IPN secret, Google OAuth client ID, Beem OTP, Cloudflare Turnstile, and SMTP email. See the files under `docs/` for each one.

## Project structure

```
backend/           Django project (config/) + apps/
  apps/
    accounts/      auth, Google sign-in, email + phone verification helpers
    catalog/       services, categories, pricing rules
    wallet/        immutable balance ledger
    orders/        order lifecycle, sync and retry tasks
    providers/     provider clients (VinaSMM JAP + mock)
    payments/      NOWPayments and mock deposit gateways
    support/       tickets
    affiliate/     referral commissions
    promotions/    coupons
    announcements/ dashboard banners
    panelapi/      reseller API endpoints
    common/        exchange-rate snapshots, shared helpers
frontend/          React (Vite) single-page app
docker/            backend and frontend Dockerfiles
docs/              integration setup notes (payments, email, OTP, provider)
```

## Testing

Backend tests use `config/settings/test.py` (in-memory SQLite) and run with pytest:

```bash
cd backend
pytest
```

Linting (ruff) is in the dev requirements:

```bash
ruff check apps config
```

Frontend ships with Vitest configured for component tests; there are currently no test files written. The production build runs the TypeScript compiler first, which catches most issues:

```bash
cd frontend
npm run build
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

If you find a security issue, do not open a public issue. Follow the disclosure policy in [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)

## Contact

Denis Wilson ([denyjoe](https://github.com/denyjoe))
