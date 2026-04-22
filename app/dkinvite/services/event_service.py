from datetime import date

from dkinvite.extensions import db
from dkinvite.models import User
from dkinvite.repositories.event_repository import EventRepository
from dkinvite.services.audit_service import AuditService

class EventService:
    @staticmethod
    def _parse_date(value: str | None):
        if not value:
            return None
        return date.fromisoformat(value)

    @staticmethod
    def list_events():
        return EventRepository.list_all()

    @staticmethod
    def create_event(*, name: str, event_date: str | None, actor: User):
        name = (name or "").strip()
        if not name:
            raise ValueError("Название мероприятия обязательно")

        exists = EventRepository.get_by_name(name)
        if exists:
            raise ValueError("Мероприятие с таким названием уже существует")

        event = EventRepository.create(
            name=name,
            event_date=EventService._parse_date(event_date),
        )
        db.session.commit()

        AuditService.log(
            user=actor,
            action="event_created",
            details=f"event_id={event.id}; name={event.name}",
        )

        return event
