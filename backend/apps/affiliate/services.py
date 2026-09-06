from decimal import ROUND_HALF_UP, Decimal

from apps.orders.models import Order
from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService

from .models import AffiliateCommission, AffiliateSettings


class AffiliateService:
    @staticmethod
    def credit_commission_for_order(order: Order) -> AffiliateCommission | None:
        """Called whenever an order transitions to COMPLETED (from both
        submit_order_to_provider and sync_order_statuses — either path an
        order can complete through). No-op if the buyer wasn't referred, if
        commission is already recorded for this order (idempotent), or if
        the order was refunded before this ran. Refunds that happen *after*
        commission was paid are NOT clawed back — the referrer may have
        already spent it; treating this as a cost of doing business rather
        than adding reversal complexity for what should be a rare case."""
        if AffiliateCommission.objects.filter(order=order).exists():
            return None

        referrer = order.user.referred_by
        if referrer is None:
            return None

        if order.refund_ledger_entry_id or order.status == Order.Status.REFUNDED:
            return None

        settings_row = AffiliateSettings.objects.first() or AffiliateSettings.objects.create()
        amount = (order.charge_amount * settings_row.commission_percent / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if amount <= 0:
            return None

        entry = WalletService.credit(
            wallet=referrer.wallet,
            amount=amount,
            entry_type=LedgerEntry.EntryType.AFFILIATE_COMMISSION,
            idempotency_key=f"affiliate-commission-order-{order.id}",
            description=f"Referral commission from an order by {order.user.email}",
            reference_type="order",
            reference_id=str(order.id),
        )
        return AffiliateCommission.objects.create(
            referrer=referrer,
            referred_user=order.user,
            order=order,
            amount=amount,
            ledger_entry=entry,
        )
