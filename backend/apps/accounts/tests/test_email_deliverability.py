from unittest.mock import patch

import dns.exception
import dns.resolver
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.email_deliverability import domain_can_receive_email
from apps.accounts.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_dns_cache():
    # domain_can_receive_email is lru_cache'd — without clearing, an earlier
    # test's mocked result for the same domain string would leak into a
    # later test that mocks a different outcome for it.
    domain_can_receive_email.cache_clear()
    yield
    domain_can_receive_email.cache_clear()


def test_domain_with_mx_record_is_accepted():
    with patch("dns.resolver.resolve", return_value=["mx.example-mx.com"]):
        assert domain_can_receive_email("has-mx.example") is True


def test_domain_with_no_mx_but_has_a_record_is_accepted():
    def fake_resolve(domain, record_type, lifetime=None):
        if record_type == "MX":
            raise dns.resolver.NoAnswer
        if record_type == "A":
            return ["1.2.3.4"]
        raise dns.resolver.NoAnswer

    with patch("dns.resolver.resolve", side_effect=fake_resolve):
        assert domain_can_receive_email("a-record-only.example") is True


def test_nonexistent_domain_is_rejected():
    with patch("dns.resolver.resolve", side_effect=dns.resolver.NXDOMAIN):
        assert domain_can_receive_email("this-domain-does-not-exist-at-all.invalid") is False


def test_domain_exists_with_no_mail_records_is_rejected():
    with patch("dns.resolver.resolve", side_effect=dns.resolver.NoAnswer):
        assert domain_can_receive_email("no-mail-records.example") is False


def test_dns_timeout_fails_open():
    with patch("dns.resolver.resolve", side_effect=dns.exception.Timeout):
        assert domain_can_receive_email("dns-is-slow-right-now.example") is True


def test_registration_rejects_nonexistent_domain(monkeypatch):
    monkeypatch.setattr(
        "apps.accounts.serializers.domain_can_receive_email", lambda domain: False
    )
    resp = APIClient().post(
        reverse("auth-register"),
        {"email": "someone@totally-made-up-domain-xyz.invalid", "password": "S3cure-Pass!"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert not User.objects.filter(email="someone@totally-made-up-domain-xyz.invalid").exists()


def test_registration_accepts_domain_with_mail_capability(monkeypatch):
    monkeypatch.setattr(
        "apps.accounts.serializers.domain_can_receive_email", lambda domain: True
    )
    resp = APIClient().post(
        reverse("auth-register"),
        {"email": "someone@example.com", "password": "S3cure-Pass!"},
    )
    assert resp.status_code == status.HTTP_201_CREATED
