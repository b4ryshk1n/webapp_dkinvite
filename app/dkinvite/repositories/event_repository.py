from sqlalchemy import select

from dkinvite.extensions import db
from dkinvite.models import Event

class EventRepository:
    @staticmethod
    def get_by_id(event_id: int) -> Event | None:
        return db.session.get(Event, event_id)

    @staticmethod
    def get_by_name(name: str) -> Event | None:
        name = (name or "").strip()
        if not name:
            return None
        return db.session.scalar(select(Event).where(Event.name == name))

    @staticmethod
    def list_all() -> list[Event]:
        query = select(Event).order_by(Event.event_date.desc(), Event.id.desc())
        return list(db.session.scalars(query).all())

    @staticmethod
    def create(*, name: str, event_date=None) -> Event:
        event = Event(name=name, event_date=event_date)
        db.session.add(event)
        return event
