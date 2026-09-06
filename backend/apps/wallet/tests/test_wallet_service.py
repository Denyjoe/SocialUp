from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.wallet.models import LedgerEntry
from apps.wallet.services import InsufficientBalanceError, WalletService

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def wallet():
    user = User.objects.create_user(email="user@example.com", password="x")
    return user.wallet  # auto-created by the post_save signal


def test_credit_increases_balance_and_records_entry(wallet):
    entry = WalletService.credit(
        wallet=wallet,
        amount=Decimal("1000.00"),
        entry_type=LedgerEntry.EntryType.DEPOSIT,
        idempotency_key="test-credit-1",
    )
    wallet.refresh_from_db()
    assert wallet.cached_balance == Decimal("1000.00")
    assert entry.balance_after == Decimal("1000.00")
    assert entry.amount == Decimal("1000.00")


def test_debit_decreases_balance(wallet):
    WalletService.credit(wallet, Decimal("1000.00"), LedgerEntry.EntryType.DEPOSIT, "credit-1")
    WalletService.debit(wallet, Decimal("400.00"), LedgerEntry.EntryType.ORDER_PAYMENT, "debit-1")
    wallet.refresh_from_db()
    assert wallet.cached_balance == Decimal("600.00")


def test_debit_beyond_balance_raises_and_leaves_balance_unchanged(wallet):
    WalletService.credit(wallet, Decimal("100.00"), LedgerEntry.EntryType.DEPOSIT, "credit-1")
    with pytest.raises(InsufficientBalanceError):
        WalletService.debit(wallet, Decimal("500.00"), LedgerEntry.EntryType.ORDER_PAYMENT, "debit-1")
    wallet.refresh_from_db()
    assert wallet.cached_balance == Decimal("100.00")
    assert not LedgerEntry.objects.filter(idempotency_key="debit-1").exists()


def test_same_idempotency_key_is_not_applied_twice(wallet):
    entry1 = WalletService.credit(wallet, Decimal("1000.00"), LedgerEntry.EntryType.DEPOSIT, "same-key")
    entry2 = WalletService.credit(wallet, Decimal("1000.00"), LedgerEntry.EntryType.DEPOSIT, "same-key")
    wallet.refresh_from_db()
    assert entry1.pk == entry2.pk
    assert wallet.cached_balance == Decimal("1000.00")  # not 2000 — the retry was a no-op
    assert LedgerEntry.objects.filter(idempotency_key="same-key").count() == 1


def test_ledger_entries_are_immutable(wallet):
    entry = WalletService.credit(wallet, Decimal("500.00"), LedgerEntry.EntryType.DEPOSIT, "immutable-1")
    entry.description = "tampered"
    from django.db import IntegrityError

    with pytest.raises(IntegrityError):
        entry.save()


def test_reconcile_matches_cached_balance(wallet):
    WalletService.credit(wallet, Decimal("1000.00"), LedgerEntry.EntryType.DEPOSIT, "credit-1")
    WalletService.debit(wallet, Decimal("300.00"), LedgerEntry.EntryType.ORDER_PAYMENT, "debit-1")
    wallet.refresh_from_db()
    assert WalletService.reconcile(wallet) is True
