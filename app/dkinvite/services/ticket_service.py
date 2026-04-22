from datetime import datetime, timezone

from dkinvite.extensions import db
from dkinvite.models import TicketStatus, User
from dkinvite.repositories.event_repository import EventRepository
from dkinvite.repositories.ticket_repository import TicketRepository
from dkinvite.services.audit_service import AuditService
from dkinvite.services.qr_service import QrService
from dkinvite.utils.validators import normalize_person_name, normalize_seat

class TicketService:
    @staticmethod
    def list_tickets(*, event_id: int | None = None, status: str | None = None):
        return TicketRepository.list_all(event_id=event_id, status=status)

    @staticmethod
    def get_ticket(ticket_id: str):
        ticket_id = (ticket_id or "").strip()
        if not ticket_id:
            raise LookupError("Билет не найден")
        ticket = TicketRepository.get_by_id(ticket_id)
        if not ticket:
            raise LookupError("Билет не найден")
        return ticket

    @staticmethod
    def create_ticket(
        *,
        event_id: int,
        owner_name: str,
        seat: str,
        actor: User,
    ):
        owner_name = normalize_person_name(owner_name)
        seat = normalize_seat(seat)

        event = EventRepository.get_by_id(event_id)
        if not event:
            raise LookupError("Мероприятие не найдено")

        exists = TicketRepository.get_by_event_and_seat(event_id, seat)
        if exists:
            raise ValueError("Это место уже занято для данного мероприятия")

        ticket = TicketRepository.create(
            ticket_id=None,
            event_id=event_id,
            owner_name=owner_name,
            seat=seat,
            status=TicketStatus.active,
        )

        db.session.flush()
        ticket.qr_path = QrService.generate_for_ticket(ticket.id)
        db.session.commit()

        AuditService.log(
            user=actor,
            action="ticket_created",
            ticket_id=ticket.id,
            details=f"event_id={event_id}; seat={seat}; owner_name={owner_name}",
        )

        return ticket

    @staticmethod
    def mark_used(*, ticket_id: str, actor: User):
        ticket = TicketService.get_ticket(ticket_id)

        if ticket.status == TicketStatus.used:
            raise ValueError("Билет уже был погашен")

        if ticket.status == TicketStatus.cancelled:
            raise ValueError("Билет отменен и не может быть погашен")

        if ticket.status == TicketStatus.blocked:
            raise ValueError("Билет заблокирован и не может быть погашен")

        if ticket.status != TicketStatus.active:
            raise ValueError("Билет недоступен для погашения")

        ticket.status = TicketStatus.used
        ticket.used_at = datetime.now(timezone.utc)
        db.session.commit()

        AuditService.log(
            user=actor,
            action="ticket_used",
            ticket_id=ticket.id,
            details=f"event_id={ticket.event_id}; seat={ticket.seat}",
        )

        return ticket

    @staticmethod
    def reset_ticket(*, ticket_id: str, actor: User):
        ticket = TicketService.get_ticket(ticket_id)

        if ticket.status == TicketStatus.active:
            raise ValueError("Билет уже активен, сброс не требуется")

        if ticket.status == TicketStatus.cancelled:
            raise ValueError("Нельзя сбросить отмененный билет")

        if ticket.status == TicketStatus.blocked:
            raise ValueError("Нельзя сбросить заблокированный билет")

        if ticket.status != TicketStatus.used:
            raise ValueError("Сброс возможен только для погашенного билета")

        ticket.status = TicketStatus.active
        ticket.used_at = None
        db.session.commit()

        AuditService.log(
            user=actor,
            action="ticket_reset",
            ticket_id=ticket.id,
            details=f"event_id={ticket.event_id}; seat={ticket.seat}",
        )

        return ticket

    @staticmethod
    def delete_ticket(*, ticket_id: str, actor: User):
        ticket = TicketService.get_ticket(ticket_id)

        details = f"event_id={ticket.event_id}; seat={ticket.seat}; owner_name={ticket.owner_name}"
        saved_id = ticket.id

        QrService.delete_for_ticket(saved_id)
        TicketRepository.delete(ticket)
        db.session.commit()

        AuditService.log(
            user=actor,
            action="ticket_deleted",
            ticket_id=saved_id,
            details=details,
        )
