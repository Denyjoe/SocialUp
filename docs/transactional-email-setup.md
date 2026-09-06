# Transactional email — setup

Used to send the "verify your email" link on registration
(`apps/accounts/tasks.py::send_verification_email`). Django's `EMAIL_*`
settings are provider-agnostic (plain SMTP) — any provider that hands you
SMTP credentials works with zero code changes.

## Recommended: Brevo (free tier — 300 emails/day)

1. Sign up at https://www.brevo.com/.
2. **SMTP & API → SMTP** — Brevo gives you an SMTP login + a generated SMTP key (not your account password).
3. Set in `backend/.env`:
   ```
   EMAIL_HOST=smtp-relay.brevo.com
   EMAIL_PORT=587
   EMAIL_HOST_USER=<your Brevo SMTP login>
   EMAIL_HOST_PASSWORD=<your Brevo SMTP key>
   EMAIL_USE_TLS=True
   DEFAULT_FROM_EMAIL=no-reply@yourdomain.com
   ```
4. For `DEFAULT_FROM_EMAIL` to not land in spam, verify a sending domain in Brevo (SPF/DKIM records) once you have a real domain — using an unverified/free-email-provider "from" address works for testing but hurts deliverability.

## Any other provider

SendGrid, Mailgun, AWS SES, Postmark, etc. all work identically — just their
own SMTP host/port/credentials in the same env vars above. Don't use your
own personal Gmail/Outlook SMTP for anything beyond a quick local test —
those get rate-limited and flagged fast at any real volume.

## Local development

Nothing to configure — `config/settings/local.py` uses Django's console
email backend, so verification emails print straight to your `runserver`
terminal instead of actually sending. Grab the link from there while testing.
