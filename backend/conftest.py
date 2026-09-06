import pytest


@pytest.fixture(autouse=True)
def _no_real_dns_lookups_by_default(monkeypatch):
    """Registration validates the email domain via a real DNS lookup
    (apps/accounts/email_deliverability.py). Defaulting every test to "yes,
    it can receive mail" keeps the suite fast and network-independent —
    apps/accounts/tests/test_email_deliverability.py tests the real DNS
    logic directly against a mocked `dns.resolver.resolve`, one level below
    this, and overrides this default per-test where it needs to."""
    monkeypatch.setattr("apps.accounts.serializers.domain_can_receive_email", lambda domain: True)
