from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import select

from dkinvite import create_app
from dkinvite.extensions import db
from dkinvite.models import Event, Ticket
from dkinvite.services.qr_service import QrService

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        event = db.session.scalar(select(Event).where(Event.name == args.name))
        if not event:
            raise SystemExit("Мероприятие не найдено")

        tickets = list(db.session.scalars(select(Ticket).where(Ticket.event_id == event.id)).all())

        for ticket in tickets:
            QrService.delete_for_ticket(ticket.id)
            db.session.delete(ticket)

        db.session.delete(event)
        db.session.commit()

        print(f"Удалено мероприятие: {event.name}")
        print(f"Удалено билетов: {len(tickets)}")

if __name__ == "__main__":
    main()
