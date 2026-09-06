"""Real-time domain-level deliverability check for registration — rejects
obviously-fake or mistyped domains (no mail server at all) without an
external paid service.

Important honesty note: this checks that the *domain* can receive mail
(has an MX or fallback A/AAAA record) — it does NOT confirm the specific
*mailbox* exists. There is no free, reliable way to check "does
someone@gmail.com actually exist" — major providers (Gmail, Outlook, etc.)
deliberately don't support SMTP-level mailbox probing, to prevent spammers
from harvesting valid addresses. The mailbox-level guarantee in this app
comes from the email-verification-link flow (apps/accounts/tasks.py) plus
the order-creation gate requiring email_verified — if nobody can read the
mailbox, they can never click the link, so they never get past that gate.
A paid verification API (ZeroBounce, Kickbox, etc.) is the only way to get
a real-time mailbox-existence signal at registration time; not used here.
"""

from functools import lru_cache

import dns.exception
import dns.resolver

DNS_TIMEOUT_SECONDS = 3.0


@lru_cache(maxsize=2048)
def domain_can_receive_email(domain: str) -> bool:
    """True if the domain has an MX record, or (per the RFC 5321 fallback)
    an A/AAAA record to deliver to directly. Fails OPEN (returns True) on a
    DNS timeout or resolver error — a transient DNS hiccup should never
    block a real user from registering. Only a domain that definitively
    doesn't exist (NXDOMAIN) or definitively has no way to receive mail is
    rejected."""
    domain = domain.lower().strip()

    try:
        return bool(dns.resolver.resolve(domain, "MX", lifetime=DNS_TIMEOUT_SECONDS))
    except dns.resolver.NoAnswer:
        pass  # domain exists but has no MX — fall through to the A/AAAA check
    except dns.resolver.NXDOMAIN:
        return False  # domain doesn't exist at all — definitive rejection
    except dns.exception.DNSException:
        return True  # timeout / temporary resolver failure — fail open

    for record_type in ("A", "AAAA"):
        try:
            if dns.resolver.resolve(domain, record_type, lifetime=DNS_TIMEOUT_SECONDS):
                return True
        except dns.exception.DNSException:
            continue

    return False  # domain exists but has nowhere to deliver mail
