from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum

from .models import LedgerEntry, Wallet


class InsufficientBalanceError(Exception):
    pass


class WalletService:
    """The only code allowed to move money in or out of a Wallet. Every call
    is idempotent on `idempotency_key` — retried webhooks, Celery retries, or
    double-clicks never double-credit or double-debit."""

    @staticmethod
    def _existing_entry(idempotency_key: str) -> LedgerEntry | None:
        return LedgerEntry.objects.filter(idempotency_key=idempotency_key).first()

    @classmethod
    def credit(
        cls,
        wallet: Wallet,
        amount: Decimal,
        entry_type: str,
        idempotency_key: str,
        description: str = "",
        reference_type: str = "",
        reference_id: str = "",
        created_by=None,
    ) -> LedgerEntry:
        return cls._apply(
            wallet, amount, entry_type, idempotency_key, description, reference_type, reference_id, created_by
        )

    @classmethod
    def debit(
        cls,
        wallet: Wallet,
        amount: Decimal,
        entry_type: str,
        idempotency_key: str,
        description: str = "",
        reference_type: str = "",
        reference_id: str = "",
        created_by=None,
    ) -> LedgerEntry:
        return cls._apply(
            wallet, -amount, entry_type, idempotency_key, description, reference_type, reference_id, created_by
        )

    @classmethod
    def _apply(
        cls,
        wallet: Wallet,
        signed_amount: Decimal,
        entry_type: str,
        idempotency_key: str,
        description: str,
        reference_type: str,
        reference_id: str,
        created_by,
    ) -> LedgerEntry:
        existing = cls._existing_entry(idempotency_key)
        if existing:
            return existing

        with transaction.atomic():
            locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
            new_balance = locked_wallet.cached_balance + signed_amount
            if new_balance < 0:
                raise InsufficientBalanceError(
                    f"Wallet {locked_wallet.pk} balance {locked_wallet.cached_balance} "
                    f"is insufficient for a change of {signed_amount}."
                )
            try:
                entry = LedgerEntry.objects.create(
                    wallet=locked_wallet,
                    amount=signed_amount,
                    balance_after=new_balance,
                    entry_type=entry_type,
                    reference_type=reference_type,
                    reference_id=str(reference_id) if reference_id else "",
                    idempotency_key=idempotency_key,
                    description=description,
                    created_by=created_by,
                )
            except IntegrityError:
                # Lost a race on the idempotency key — a concurrent call already
                # processed this exact operation; return that entry instead.
                existing = cls._existing_entry(idempotency_key)
                if existing:
                    return existing
                raise

            locked_wallet.cached_balance = new_balance
            locked_wallet.save(update_fields=["cached_balance", "cached_balance_updated_at"])
            return entry

    @staticmethod
    def reconcile(wallet: Wallet) -> bool:
        """True if cached_balance matches the sum of this wallet's ledger entries."""
        total = wallet.ledger_entries.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        return total == wallet.cached_balance
