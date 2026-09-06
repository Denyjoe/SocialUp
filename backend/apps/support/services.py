from .models import Ticket, TicketMessage


class SupportService:
    @staticmethod
    def create_ticket(user, subject: str, category: str, message_body: str, order=None) -> Ticket:
        ticket = Ticket.objects.create(
            user=user,
            subject=subject,
            category=category,
            order=order,
            status=Ticket.Status.OPEN,
        )
        TicketMessage.objects.create(ticket=ticket, sender=user, body=message_body)
        return ticket

    @staticmethod
    def add_message(ticket: Ticket, sender, body: str, attachment=None) -> TicketMessage:
        message = TicketMessage.objects.create(
            ticket=ticket, sender=sender, body=body, attachment=attachment
        )
        # Auto-transition status based on who just spoke, so the queue always
        # reflects whose turn it is to respond.
        if sender.is_staff:
            ticket.status = Ticket.Status.ANSWERED
        else:
            ticket.status = (
                Ticket.Status.OPEN if ticket.status == Ticket.Status.OPEN else Ticket.Status.PENDING
            )
        ticket.save(update_fields=["status", "updated_at"])
        return message
