import json
import uuid
from decimal import Decimal

from django.db import transaction as db_transaction

from apps.common import exchange
from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService

from .gateways.exceptions import PaymentGatewayError
from .gateways.registry import get_gateway
from .models import Transaction

# Below this, network fees alone can eat most of a crypto deposit — not a
# NOWPayments-imposed limit, just this panel's own sanity floor.
MIN_DEPOSIT_USD = Decimal("5.00")

# Reaching a wallet at all only ever happens on "finished". NOWPayments
# explicitly advises against treating "partially_paid" as good funds
# received (a customer sending less than quoted is expected and normal for
# crypto) — their own docs point to manual admin review for that case
# rather than auto-crediting a partial, different amount than what was
# quoted. Left visible on the transaction for the admin to resolve, never
# auto-settled.
SETTLING_STATUS = Transaction.Status.FINISHED


class PaymentValidationError(Exception):
    pass


def _quote_rates() -> dict:
    """The customer-currency-display FX snapshot, refreshed on demand if
    none exists yet — e.g. a fresh install, before the hourly beat task has
    ever run. Reuses apps.common.tasks.refresh_exchange_rates' own
    snapshot-creation logic rather than duplicating it."""
    from apps.common.models import ExchangeRateSnapshot

    snapshot = ExchangeRateSnapshot.latest()
    if snapshot is not None:
        return snapshot.rates

    from apps.common.tasks import refresh_exchange_rates

    refresh_exchange_rates()
    snapshot = ExchangeRateSnapshot.latest()
    if snapshot is None:
        raise PaymentValidationError(
            "Exchange rates are temporarily unavailable. Please try again shortly."
        )
    return snapshot.rates


class PaymentService:
    @staticmethod
    def create_deposit(*, user, amount_local: Decimal, gateway_name: str = "nowpayments") -> Transaction:
        if amount_local <= 0:
            raise PaymentValidationError("Enter an amount greater than zero.")

        rates = _quote_rates()
        try:
            amount_quote = exchange.convert(amount_local, "USD", rates)
        except exchange.ExchangeRateError as exc:
            raise PaymentValidationError(str(exc)) from exc

        if amount_quote < MIN_DEPOSIT_USD:
            raise PaymentValidationError(
                f"The minimum deposit is the equivalent of ${MIN_DEPOSIT_USD}."
            )

        txn = Transaction.objects.create(
            user=user,
            gateway=gateway_name,
            internal_reference=f"dep-{uuid.uuid4().hex[:20]}",
            amount_local=amount_local,
            amount_quote=amount_quote,
            quote_currency="usd",
            status=Transaction.Status.WAITING,
        )

        gateway = get_gateway(gateway_name)
        try:
            result = gateway.create_checkout(transaction=txn)
        except PaymentGatewayError as exc:
            txn.status = Transaction.Status.FAILED
            txn.raw_payload = {"error": str(exc)}
            txn.save(update_fields=["status", "raw_payload", "updated_at"])
            raise PaymentValidationError(
                "Could not start the payment. Please try again shortly."
            ) from exc

        txn.gateway_reference = result.gateway_reference
        txn.checkout_url = result.checkout_url
        txn.save(update_fields=["gateway_reference", "checkout_url", "updated_at"])

        if result.immediate_status:
            PaymentService._settle(txn, new_status=result.immediate_status, raw={"mock": True})
            txn.refresh_from_db()

        return txn

    @staticmethod
    def handle_webhook(*, gateway_name: str, raw_body: bytes, signature: str) -> Transaction:
        gateway = get_gateway(gateway_name)
        if not gateway.verify_webhook_signature(raw_body=raw_body, signature=signature):
            raise PaymentValidationError("Invalid webhook signature.")

        payload = json.loads(raw_body)
        result = gateway.parse_webhook(payload)
        if not result.internal_reference:
            raise PaymentValidationError("Webhook did not reference a known deposit.")

        txn = Transaction.objects.select_related("user__wallet").get(
            internal_reference=result.internal_reference, gateway=gateway_name
        )
        return PaymentService._settle(
            txn, new_status=result.status, raw=payload, pay_currency=result.pay_currency
        )

    @staticmethod
    @db_transaction.atomic
    def _settle(txn: Transaction, *, new_status: str, raw: dict, pay_currency: str = "") -> Transaction:
        """The single place a deposit's status changes and, if warranted,
        the wallet actually gets credited. `ledger_entry_id` already being
        set is checked before crediting again — belt-and-suspenders on top
        of WalletService's own idempotency-key check, since NOWPayments'
        own docs say a webhook can legitimately be resent on a timeout."""
        txn.raw_payload = raw
        if pay_currency:
            txn.pay_currency = pay_currency
        txn.status = new_status
        txn.save(update_fields=["status", "raw_payload", "pay_currency", "updated_at"])

        if new_status == SETTLING_STATUS and not txn.ledger_entry_id:
            entry = WalletService.credit(
                wallet=txn.user.wallet,
                amount=txn.amount_local,
                entry_type=LedgerEntry.EntryType.DEPOSIT,
                idempotency_key=f"deposit-{txn.id}",
                description=f"Wallet deposit via {txn.get_gateway_display()}",
            )
            txn.ledger_entry = entry
            txn.save(update_fields=["ledger_entry", "updated_at"])

        return txn
