import uuid
from decimal import Decimal

from django.db import transaction

from apps.catalog.models import Service
from apps.catalog.routing import resolve_best_mapping
from apps.promotions.models import CouponError
from apps.promotions.services import PromotionService
from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService

from .models import Order, OrderStatusHistory
from .tasks import submit_order_to_provider


class OrderValidationError(Exception):
    pass


class OrderService:
    @staticmethod
    def create_order(
        user, service: Service, link: str, quantity: int, coupon_code: str = ""
    ) -> Order:
        # Email is the identity gate. Phone is deliberately NOT gated — it's
        # optional, collected only for sending customers updates. Google
        # sign-ins arrive with email_verified already True (Google verified
        # the address), so they pass straight through with no extra step.
        if not user.email_verified:
            raise OrderValidationError(
                "Please verify your email address before placing your first order. "
                "Check your inbox for the verification link."
            )
        if not service.is_active:
            raise OrderValidationError("This service is not currently available.")
        if quantity < service.min_quantity or quantity > service.max_quantity:
            raise OrderValidationError(
                f"Quantity must be between {service.min_quantity} and {service.max_quantity}."
            )

        # Smart API Auto-Routing groundwork: picks the cheapest active,
        # healthy mapping right now (today, always the service's one and
        # only mapping — see apps.catalog.routing). Resolved before the
        # wallet is touched, and snapshotted onto the order itself, so a
        # later re-resolve (e.g. after a price change) can never disagree
        # with what was actually charged and submitted.
        mapping = resolve_best_mapping(service)
        if mapping is None:
            raise OrderValidationError("This service has no available provider right now.")

        list_amount = service.calculate_charge(quantity)

        # Resolve the coupon before opening the transaction so an invalid
        # code fails fast without touching the wallet. CouponError messages
        # are written to be shown to the customer as-is.
        coupon = None
        discount_amount = Decimal("0.00")
        if coupon_code:
            try:
                coupon = PromotionService.resolve_coupon(coupon_code, user, list_amount)
            except CouponError as exc:
                raise OrderValidationError(str(exc)) from exc
            discount_amount = coupon.discount_for(list_amount)

        charge_amount = list_amount - discount_amount
        wallet = user.wallet

        with transaction.atomic():
            entry = WalletService.debit(
                wallet=wallet,
                amount=charge_amount,
                entry_type=LedgerEntry.EntryType.ORDER_PAYMENT,
                idempotency_key=f"order-create-{uuid.uuid4()}",
                description=f"Order for {service.name} x{quantity}",
            )
            order = Order.objects.create(
                user=user,
                service=service,
                provider=mapping.provider,
                provider_service_id=mapping.provider_service_id,
                link=link,
                quantity=quantity,
                charge_amount=charge_amount,
                discount_amount=discount_amount,
                cost_amount=(mapping.cost_rate_per_1000 * quantity) / Decimal(1000),
                cost_currency=service.cost_currency,
                status=Order.Status.PENDING,
                ledger_entry=entry,
            )
            if coupon is not None:
                # Inside the transaction, so a failed charge never burns a coupon.
                PromotionService.redeem(coupon, user, discount_amount, order=order)
            OrderStatusHistory.objects.create(
                order=order,
                old_status="",
                new_status=Order.Status.PENDING,
                source=OrderStatusHistory.Source.USER,
            )
            transaction.on_commit(lambda: submit_order_to_provider.delay(str(order.id)))

        return order

    @staticmethod
    def refund_order(order: Order, reason: str = "") -> Order:
        if order.refund_ledger_entry_id:
            return order  # already refunded — idempotent no-op

        entry = WalletService.credit(
            wallet=order.user.wallet,
            amount=order.charge_amount,
            entry_type=LedgerEntry.EntryType.ORDER_REFUND,
            idempotency_key=f"order-refund-{order.id}",
            description=reason or f"Refund for order {order.id}",
        )
        old_status = order.status
        order.refund_ledger_entry = entry
        order.status = Order.Status.REFUNDED
        order.save(update_fields=["refund_ledger_entry", "status", "updated_at"])
        OrderStatusHistory.objects.create(
            order=order,
            old_status=old_status,
            new_status=Order.Status.REFUNDED,
            source=OrderStatusHistory.Source.SYSTEM_SYNC,
        )
        return order
