from sqlalchemy import select

from dkinvite.extensions import db
from dkinvite.models import Ticket, TicketStatus

class TicketRepository:
    @staticmethod
    def get_by_id(ticket_id: str) -> Ticket | None:
        ticket_id = (ticket_id or "").strip()
        if not ticket_id:
            return None
        return db.session.get(Ticket, ticket_id)

    @staticmethod
    def get_by_event_and_seat(event_id: int, seat: str) -> Ticket | None:
        return db.session.scalar(
            select(Ticket).where(
                Ticket.event_id == event_id,
                Ticket.seat == seat,
            )
        )

    @staticmethod
    def list_all(
        *,
        event_id: int | None = None,
        status: str | None = None,
    ) -> list[Ticket]:
        query = select(Ticket)

        if event_id is not None:
            query = query.where(Ticket.event_id == event_id)

        if status:
            try:
                query = query.where(Ticket.status == TicketStatus(status))
            except ValueError:
                raise ValueError("Некорректный статус билета")

        query = query.order_by(Ticket.created_at.desc())
        return list(db.session.scalars(query).all())

    @staticmethod
    def create(
        *,
        ticket_id: str | None,
        event_id: int,
        owner_name: str,
        seat: str,
        status,
    ) -> Ticket:
        payload = {
            "event_id": event_id,
            "owner_name": owner_name,
            "seat": seat,
            "status": status,
        }
        if ticket_id:
            payload["id"] = ticket_id

        ticket = Ticket(**payload)
        db.session.add(ticket)
        return ticket

    @staticmethod
    def delete(ticket: Ticket) -> None:
        db.session.delete(ticket)
