import uuid
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.wallet.models import LedgerEntry, Wallet
from apps.wallet.services import WalletService

User = get_user_model()


class Command(BaseCommand):
    help = "Credits a user's wallet by a fixed amount — handy for local testing."

    def add_arguments(self, parser):
        parser.add_argument("email", type=str)
        parser.add_argument("amount", type=str, help="e.g. 50000")

    def handle(self, *args, **options):
        try:
            amount = Decimal(options["amount"])
        except InvalidOperation as exc:
            raise CommandError(f"Invalid amount: {options['amount']!r}") from exc

        try:
            user = User.objects.get(email=options["email"])
        except User.DoesNotExist as exc:
            raise CommandError(f"No user with email {options['email']!r}") from exc

        wallet, _ = Wallet.objects.get_or_create(user=user)
        entry = WalletService.credit(
            wallet=wallet,
            amount=amount,
            entry_type=LedgerEntry.EntryType.ADMIN_ADJUSTMENT_CREDIT,
            idempotency_key=f"cli-grant-{wallet.pk}-{uuid.uuid4().hex[:8]}",
            description="Credited via credit_wallet management command",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Credited {amount} {wallet.currency} to {user.email}. New balance: {entry.balance_after}."
            )
        )
